# V14 — run log

| Field | Value |
|---|---|
| Ticket | V14 of `plans/msca_dn_historical_validation_tickets.md` (Stage A historical experiment), lane H2 |
| Runbook | `plans/msca_dn_pe09_runbook.md` §4–§6 |
| Bundle | O5: tag `msca-dn-freeze-2026-11-12`, revision `17e32d54`, under `bundles/msca-dn-freeze-2026-11-12/` |
| Kept by | agent (Claude), from the operator's decisions in session. The agent sees no proposal text and runs no model call |
| Step sheet | `STEPS.md`: part W (workstation) written; part H (host) outlined, its scripts follow the measured cost |
| Rehearsal | `REHEARSAL.md`, scripts in `rehearsal/` |

## Settling

| When | Who | What |
|---|---|---|
| 2026-11-12 | operator | V14-OP1 to V14-OP4 below, in session |
| 2026-11-12 | agent | V14-F1 and V14-F2 measured. Cost statement written (below). No go given |
| 2026-11-12 | operator | V14-OP6 to V14-OP8 below, in session. Then the operator does the real import and the workstation preflight |
| 2026-11-12 | operator | V14-F5 answered, OP7 date given, V14-A1 accepted, V14-F3 to be noted for V16, in session. The operator runs W01–W08 next |
| 2026-11-12 | agent | Route (ii) rehearsed (`REHEARSAL.md` R14–R22): the re-rendered register loads against the frozen baseline. V14-F6 found |
| 2026-11-12 | operator | W01–W08 in progress. W07 failed closed at the default package budget and passes with `--package-budget <B>`. Recorded as V14-F7; the flag goes on the host preflight, assess and audit lines |
| 2026-11-12 | agent | Rehearsal run (`REHEARSAL.md`): V14-F2 settled by the supplement (`supplement.json`); V14-F3 to V14-F5 found; V14-A1 decided. `STEPS.md`, `workstation/v14_pack.py`, `workstation/v14_cost.py` written. No AWS call, no model call. No go given |

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
- **V14-OP6. Rehearsal and the supplement.** Rehearse on the workstation, and extend it to the §6 commands in the
  bundle-only tree over the committed sanitised artifacts. Then option (a): ship the listed public files from the
  freeze tag as a supplement, sha256 recorded, and use the same files for V16.
- **V14-OP7. Private outputs after teardown.** An encrypted EBS snapshot, at final teardown only. Before it, check
  the volume for credential material. Show that the snapshot is private and encrypted. Record the deletion date the
  operator gives. No IAM change.
- **V14-OP8. Session logging.** The step that reads the account's session preferences is accepted. Sessions use
  the default document only.
- **V14-OP9. The register's declarations (answers V14-F5).** Route (iii) for the first comparison: no
  `fidelity_to_submitted_original` block, so such misses stand `Inferred`. Route (ii) as its successor, only for
  misses whose diagnosis needs `Confirmed`: declare and re-render on the workstation, ship the register in a second
  inbound archive by the V14-OP1 route. Not route (i): declaring before packing would put ESR material in the root
  before the freeze.
- **V14-OP7, date.** Delete the snapshot 30 days after V16 is confirmed, and no later than 2027-03-31. The
  snapshot carries that date as a tag. While V16 is unconfirmed the tag reads 2027-03-31; when V16 is confirmed the
  agent computes the earlier date and the operator re-tags it.

### Agent decision

- **V14-A1. The archive holds less than the whole private root.** The rehearsal ran the host chain on a root
  without the PDF, the dry-import records and the configuration input: same exits, same pack set (REHEARSAL.md R9,
  R10, R12). So `v14_pack.py` ships the workspace, the register and the supplement, and refuses a PDF or a
  dry-import record. The original's PDF never reaches the host. **Accepted** by the operator, 2026-11-12.

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
  `converse_smoke` writes its own synthetic profile and registry. **Settled** by V14-OP6 and the rehearsal:
  every command runs with `--repo-root <private root>`, and the ten files of `supplement.json` sit under it at
  their repository paths. One is outside the bundle (the registry), eight are bundle files the commands resolve
  under `--repo-root`, and one is the dispositions template. In the bundle-only tree, §5 and the §6 audit passed
  over the historical profile, and §6 audit, compare, review and diff passed over the sanitised artifacts.
- **V14-F3. Runbook step 1c refuses as written at the tag.** `py -m tools.import_external_proposal` runs the importer
  as `__main__`. The register renderer imports `tools.import_external_proposal` again, a second module whose
  registry lacks the revision declared at run time, so the import refuses: `revision 'as_submitted_v1' belongs to
  no declared document`. It writes `sources.json` first. The test suite calls the importer in-process and never
  sees this. For V14, `STEPS.md` W05 calls the same code in-process, so nothing is built from `harness_overhaul`
  (O5). The fix belongs to `harness_overhaul` after V16. **Noted for V16** (operator, 2026-11-12): its stage-B
  import (runbook §8) has the same line, so V16 uses the same in-process form with
  `--document resubmission_2026`; the note sits on the V16 ticket.
- **V14-F4. `diff` loads the repository default profile.** It reads `harness/profiles/msca_pf_default.json`, its
  scorecard and its rubrics under `--repo-root`, whatever profile the two comparisons used. Covered by the
  supplement. Whether `diff`'s output depends on that profile is not checked (Unresolved).
- **V14-F5. The register's declarations can only be re-rendered on the workstation.** A Confirmed preservation
  claim in `compare` needs a `fidelity_to_submitted_original` block in the register's declared half (runbook §6).
  Re-rendering the register runs `tools/` code and re-extracts the PDF, and the host has neither. To decide before
  the go: (i) declare on the workstation before packing, since the ESR's observation ids are public;
  (ii) re-render on the workstation after reading the comparison, and ship the register in a second inbound
  archive; or (iii) leave such misses `Inferred`, which `compare` accepts without the block. **Answered** by
  V14-OP9: (iii), then (ii) as successor. Route (ii) rehearsed: REHEARSAL.md R14–R22.
- **V14-F6. `diff` does not cross a register swap.** `diff` re-hashes the register each comparison recorded. After
  route (ii) replaces the register in place, the route (iii) comparison no longer matches it, and `diff` from it
  refuses: `the fidelity register moved after the comparison was written` (REHEARSAL.md R20). `diff` between two
  comparisons over the new register works (R21). Consequence for the step sheet: finish everything that reads the
  first comparison (its `review`, and any `diff` among route (iii) comparisons) before the new register goes in, and
  read the first comparison against its successor by observation id, by hand, as runbook §6 already does across
  baselines. `review` of the first comparison after the swap was not run; it re-resolves the same references, so it
  is expected to refuse too (Inferred).
- **V14-F7. The original's package exceeds the default package budget.** At W07 the preflight failed closed, exit 2:
  `package incomplete under budget 200000` (operator, 2026-11-12). The default is `DEFAULT_PACKAGE_BUDGET`
  (200,000, in the dev-graph package's own cost unit). The preflight passes with `--package-budget <B>`, where
  `<B>` is the value the operator reports. The rehearsal did not catch this, because the eleven-page fixture fits
  under the default. The budget is a ceiling, not a cut: an incomplete package is refused, so the flag drops
  nothing the blind view permits. It is a package request key (`runner/dev_graph/packages.py`), so `preflight`,
  `assess` and `audit` must all carry the same value. Those three commands take the flag, while `freeze`,
  `compare`, `review`, `diff` and the receipt validator do not. Step sheet: W07, H06 and the H08/H08b audits
  carry `--package-budget <B>`, and W08 reads the preflight made with it.

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

**Overhead measured.** The rehearsal measured the prompt overhead per call: at most 2,847 characters for a cell
call and 4,564 for a criterion call, about 712 and 1,141 tokens (REHEARSAL.md). That replaces the 4,000 tokens
assumed above. `workstation/v14_cost.py` applies it to the operator's preflight (STEPS.md W08).

The input planned figure is a guess until the original is measured. The preflight makes no model call
and reports pack sizes, so a workstation preflight over the private root replaces the guess before the
go. At the upper bound the 85% and 100% budget alerts fire. The credits cover it.
