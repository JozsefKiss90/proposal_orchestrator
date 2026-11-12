# V14 — run log

| Field | Value |
|---|---|
| Ticket | V14 of `plans/msca_dn_historical_validation_tickets.md` (Stage A historical experiment), lane H2 |
| Runbook | `plans/msca_dn_pe09_runbook.md` §4–§6 |
| Bundle | O5: tag `msca-dn-freeze-2026-11-12`, revision `17e32d54`, under `bundles/msca-dn-freeze-2026-11-12/` |
| Kept by | agent (Claude), from the operator's decisions in session. The agent sees no proposal text and runs no model call |
| Step sheet | Not written. Waits for V14-F2 to be settled |

## Settling

| When | Who | What |
|---|---|---|
| 2026-11-12 | operator | V14-OP1 to V14-OP4 below, in session |
| 2026-11-12 | agent | V14-F1 and V14-F2 measured. Cost statement written (below). No go given |

### Operator decisions

- **V14-OP1. Inbound route.** The input travels as one archive with a neutral name under `bundles/`. The
  host checks its sha256 after the fetch. All versions of the object are deleted after the fetch,
  delete markers included. The ESR record is uploaded the same way, and only after the freeze.
- **V14-OP2. What may leave the host.** The repository and the agent get metadata, numeric scores and
  spreads. Finding text, quotes, dispositions and declarations stay on the host.
- **V14-OP3. Host lifetime (deviation V14-D1).** The host stack is kept between sittings, with the
  instance stopped, until V14 is confirmed.
- **V14-OP4. Reading on the host.** The operator reads text in an interactive Session Manager session,
  never in Run Command output. The step sheet must show that session logging is off.
- **V14-OP5. Pacing.** The Converse route stays as it is (`paced=False`, 6 retries). The agent states the
  call count and cost before the go.

### Deviation

- **V14-D1. OD5 is not followed for V14.** OD5 creates the endpoints-and-host stack per working session
  and deletes it afterwards (`plans/aws_redeployment_handoff_2026-10-21.md`, OD5). For V14 the stack
  lives across sittings with the instance stopped (V14-OP3). Stopped, the interface endpoints and the
  volume still bill: 0.063916 USD per hour, about 1.53 USD per day (`R14_05_cost-check/report.json`).
  The stack is deleted when V14 is confirmed, by the step 14 teardown of R15.

## Findings

- **V14-F1. The O5 bundle cannot run runbook §4.** The bundle's roots hold only one file from `tools/`
  (`tools/anonymisation_host_smoke.py`) and no `docs/`. Steps 1a–1c run `tools.import_external_proposal`,
  `tools.dry_import_original` and `tools.author_original_workspace`, none of which is in the bundle.
  Measured on the tag's `deploy/offline_bundle.json`. The operator's plan follows from this: import on
  the workstation from the `freeze_bundle` worktree (revision `17e32d54`) into a private root outside
  every checkout, then ship that root (V14-OP1).
- **V14-F2. The O5 bundle cannot run runbook §5 with the historical profile either.** The profile names
  `registry_path: docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json`.
  `harness.expectations.load_expectation_substrate` resolves it under `--repo-root`. On a tree that holds
  only the bundle's 299 files (extracted from the tag), loading fails with `expectation registry not
  found`. On the full `freeze_bundle` worktree it loads 10 expectations. R15 did not see this because
  `converse_smoke` writes its own synthetic profile and registry. Whether §5 reads any other file
  outside the bundle is not yet known. A rehearsal finds out (see the agent's proposal in session).

Measured and found clear:

- The profile itself, `harness.historical_profile.load_historical_profile` and the receipt's profile
  discovery all load from the bundle-only tree.
- `assess --intake` reads the intake record under `--graph-root`, which is the private root.
- The importer writes paths relative to the root, in POSIX form, so the root can move from Windows to
  Linux.
- The extraction pin is PyMuPDF 1.28.2 on both sides (workstation 3.10.6, host bundle
  `deploy/requirements-host.txt`). §5 does not read it.
- The ESR record is a committed repository file. The private root only names it, so an archive of the
  root made before the freeze holds no ESR bytes.
- The host stack has the `ssmmessages` endpoint that an interactive session needs (`90-host.yaml`).

## Cost statement (agent, before any go)

**Calls.** 45 Converse calls: 10 expectations × 3 samples (`--n` default) plus 3 criteria × 5 samples
(`--criterion-n` default). The sanitised 2026-profile baseline made the same split: 45 live calls.
Throttled calls are retried, up to 6 times. Malformed answers add calls.

| Item | Planned | Upper bound | Basis |
|---|---|---|---|
| Bedrock input | about 675,000 tokens, 2.23 USD | 45 × 36,768 tokens, plus 20% for retries: 6.55 USD | Pack and criterion budgets on Converse are uncapped defaults of 32,768 tokens each. Instructions and rubric taken as about 4,000 tokens per call (Assumed). Planned assumes about 15,000 tokens per call (Assumed). 3.3 USD per 1M tokens |
| Bedrock output | about 45,000 tokens, 0.74 USD | 45 × 2,048 tokens, plus 20%: 1.82 USD | `max_tokens` 2048 as in R15's receipt. 16.5 USD per 1M tokens |
| Host running | 2 sittings × 2 h: 0.62 USD | 3 sittings × 3 h: 1.39 USD | 0.154686 USD per running hour |
| Host stopped (V14-D1) | 3 days: 4.60 USD | 7 days: 10.74 USD | 0.063916 USD per stopped hour |
| **V14** | **about 8.2 USD** | **about 20.5 USD** | Budget 10 USD per month; credits 199.19 USD at R15 step 01 |

The input planned figure is a guess until the original is measured. The preflight makes no model call
and reports pack sizes, so a workstation preflight over the private root replaces the guess before the
go. At the upper bound the 85% and 100% budget alerts fire. The credits cover it.
