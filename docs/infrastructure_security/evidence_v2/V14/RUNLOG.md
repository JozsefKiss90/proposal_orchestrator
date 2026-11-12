# V14 — run log

| Field | Value |
|---|---|
| Ticket | V14 of `plans/msca_dn_historical_validation_tickets.md` (Stage A historical experiment), lane H2 |
| Runbook | `plans/msca_dn_pe09_runbook.md` §4–§6 |
| Bundle | O5: tag `msca-dn-freeze-2026-11-12`, revision `17e32d54`, under `bundles/msca-dn-freeze-2026-11-12/` |
| Kept by | agent (Claude), from the operator's decisions in session. The agent sees no proposal text and runs no model call |
| Step sheet | `STEPS.md`: part W (workstation) done 2026-11-12; part H (host) written, scripts in `host/`, rehearsed (`REHEARSAL.md` R23–R31) |
| Rehearsal | `REHEARSAL.md`, scripts in `rehearsal/` |

## Settling

| When | Who | What |
|---|---|---|
| 2026-11-12 | operator | V14-OP1 to V14-OP4 below, in session |
| 2026-11-12 | agent | V14-F1 and V14-F2 measured. Cost statement written (below). No go given |
| 2026-11-12 | operator | V14-OP6 to V14-OP8 below, in session. Then the operator does the real import and the workstation preflight |
| 2026-11-12 | operator | V14-F5 answered, OP7 date given, V14-A1 accepted, V14-F3 to be noted for V16, in session. The operator runs W01–W08 next |
| 2026-11-12 | agent | Route (ii) rehearsed (`REHEARSAL.md` R14–R22): the re-rendered register loads against the frozen baseline. V14-F6 found |
| 2026-11-12 | operator | W01–W08 done (below, "The input and the workstation run"). W07: one refusal at the default package budget, three flagged runs at the default criterion budget, then the final run with both budgets (V14-F7): exit 1, pack set `sha256:fe975e4b8489`, two flags (V14-F8) |
| 2026-11-13 | agent | Measured cost in place (below). Part H written: `STEPS.md` H01–H12, `host/`, `workstation/v14_pack_one.py`; rehearsed on the synthetic root with a scripted Converse client (`REHEARSAL.md` R23–R31). Deviation V14-D2 recorded. Go asked, with points P1–P4. No go given |
| 2026-11-13 | operator | **Go given, in session**, for hourly charges from H03 until H11d and the 45-call pass at H06. P1, P3 and P4 as written; V14-D2 accepted. P2 with the operator's authority wording (below, "The go"); processing and export as drafted. Input facts reported (portal file, pages, tool); limitation V14-L1 recorded. The operator runs H01 first, then H02 with H03 at the start of sitting 1 |
| 2026-11-13 | operator | H01 run 1: every AWS call refused, "session has expired" (exit 255). No evidence counts; no AWS change. The session-preferences file read `absent` from that failure, so the H01 PASS criterion now requires `invalid_document` true for `absent`. H01 to be rerun after `aws login` |
| 2026-11-13 | operator | H01 run 2: PASS, checked by script. FREE / ACTIVE, credits 199.16 USD; one budget, limit 10.0, spend 0.601 USD; three notifications, all OK; account `797661577394`, `AccountFullAccessRole`; session document absent (`InvalidDocument`, exit 254), so no session logging; host stack does not exist (exit 254); `bundles/` holds only the O5 tarball and its `.sha256`. Next: H02 and H03 at the start of sitting 1 |
| 2026-11-13 | operator | H02 run 1: `$O` left as the placeholder `<O>`; no hash or size read, `cp_exit=255`, head-object 404. Nothing uploaded; no AWS change. H02 now refuses before any AWS call when `$O` is a placeholder or the archive is not there. To be rerun |
| 2026-11-13 | operator | H02 run 2: PASS, checked by script. Upload sha256 `406b15dc…5174`, 194,572 bytes, `cp_exit=0`; the object 194,572 bytes, `aws:kms` with the R6 project key, bucket key on, one version. Next: H03 (hourly charges start, under the go) |
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

### The input and the workstation run (operator, 2026-11-12)

- **The input.** A page extract (Part B only) of the portal's proposal PDF, declared `Inferred`. Extract sha256
  `c2caaeaa6782e11e7af4b740aff1bead1568d498fafc6ab46430d6097b92e9db`. Source: the portal file, sha256
  `195c653d835b8b3b689c2367eaa27af7ecf6ed90bc65ef88933c239d8cc94108`, pages 105–161, extracted with MS Edge by
  printing those pages to PDF (operator, 2026-11-13). Part A stays off the host.
- **Limitation V14-L1.** Printing to PDF re-renders the pages; it is not a lossless page copy. The extract's bytes,
  fonts and text layer can differ from the portal file's pages 105–161. So the extract's hash binds the run to the
  extract, not to the portal file. That the extract is the submitted Part B is the operator's declaration, not a
  measurement.
- **The configuration's status note** (as the operator reports it): "Page count, body point size, page map and
  markers reconciled against the PDF by the operator on 2026-11-12, using the dry import's worksheet. The PDF is a
  page extract (Part B only) of the portal's proposal PDF: portal file sha256
  195c653d835b8b3b689c2367eaa27af7ecf6ed90bc65ef88933c239d8cc94108, pages 105-161 of that file, extracted with MS
  Edge. That the extract is the submitted Part B is the operator's declaration, not a measurement."
- **W03.** `--describe` and `--environment` exit 0, the environment on the pin. Dry import: one refusal (a
  placeholder left in), two runs with wrong identifiers, the output folder deleted, then one clean run, exit 0. The
  acceptance record complete; `--check-acceptance` exit 0.
- **W04.** Exit 0, findings 0, unchecked 0. Pages declared 57, measured 57, mapped 53.
- **W05.** Refused once (the acceptance record not yet marked complete), then exit 0, findings 0, unchecked 0, three
  files written.
- **W06.** `freeze_revision=17e32d54…` `clean=yes`; 13 worktrees checked, root and output outside; 10 supplement
  files, sha256 ok; no ESR record under the root. Archive `input-20261112-40eb1f.tar.gz`, 194,572 bytes, sha256
  `406b15dcb1f790da957faf6720b338c908511fc4716b8b4f79f1ace126605174`; 19 members: workspace 8, register 1,
  supplement 10.
- **W07.** As V14-F7 and V14-F8.
- **W08.** 10 packs complete, none unbuilt; 3 criteria, none incomplete. Pack tokens 63,965 in all, 12,807 the
  largest. Criterion inputs 34,168, 11,895 and 26,340 tokens. 45 calls (`n` 3, `criterion_n` 5). The freeze
  worktree's `status` printed nothing.
- **Map decisions (operator).** Pages 1–4 lie outside the map: front matter and table of contents. Sections 9 and 10
  are mapped as sub-sections. Sub-section 3.2 ends on page 33. The work-package labels are taken from the sanitised
  copy's declaration, without a label-by-label check against the original (Assumed).

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
- **V14-D2. The host lines are run by driver scripts, with an explicit checkpoint.** Runbook §5 writes the
  commands as `python -m harness.commands.blind_assessment …` lines, and its documented assess line names no
  checkpoint. On the host, `host/v14_h05a_prepare.sh` writes the exact argument list to `/root/v14/prepared.json`,
  and `host/v14_h06_assess.sh` passes it to the same `main()`, in-process, as `harness.commands.converse_smoke`
  did at R15. The list carries `--checkpoint /root/v14/R/.harness/checkpoints/v14_stage_a.jsonl`, because the
  receipt must name the checkpoint path before the run (runbook §1.1). A resume therefore swaps `--checkpoint` for
  `--resume` on that path and changes nothing else, where the runbook adds `--resume` to a line without either. The
  parser accepts only one of the two. Rehearsed: REHEARSAL.md R27.

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
- **V14-F7. The original needs two non-default evidence budgets.** Found at W07 (operator, 2026-11-12), over three
  preflight runs (Settling). Both are budgets, not cuts: under the default, the commands refuse or leave a criterion
  unscored rather than drop evidence silently.
  - `--package-budget 400000`. At the default 200,000 the original's package is incomplete and the preflight
    refuses, exit 2. The budget is a package request key (`runner/dev_graph/packages.py`), so `preflight`, `assess`
    and `audit` carry the same value.
  - `--criterion-budget 40000`. At the default 32,768 (`UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET`) the excellence
    criterion's input, 34,168, does not fit and is reported not scored. The freeze would then refuse
    (`harness/blind_baseline.py`, unscored criteria). Only `preflight` and `assess` take this flag.
  - `freeze`, `compare`, `review`, `diff` and the receipt validator take neither flag.
  - The rehearsal did not catch either, because the eleven-page fixture fits both defaults.
  - A larger criterion input raises the criterion calls' input tokens. The W08 cost reads the preflight made with
    both flags, so it includes this.
- **V14-F8. The preflight's two remaining flags are explained, and neither blocks.** In the code, `assess` checks
  the preflight's parameters and pack set, not its flags, and the freeze does not read them (Inferred from the code;
  not run with a flagged preflight).
  - **Tables: 250 rows rendered and parsed, against 275 in the import manifest.** The operator explains the gap of
    25 by the 25 rows on pages 1–4, which lie outside the declared page map (operator, 2026-11-12). The map is the original's configuration, so these rows are outside the assessed sections by
    declaration, not lost by the extraction.
  - **Word scan: 111 hits.** The scan is the instance-one leak scan (`harness/evidence_preflight.py`), built to
    keep instance-one names out of a sanitised tree. Here it runs over the private, unsanitised root of the real
    original, so hits are expected and do not indicate a leak into the assessment. Only the count is recorded.
    The preflight report lists up to 50 hits by path, line and noun, so it stays private: H09 returns no
    preflight report, only its whitelisted metadata.

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

**Measured** by the operator's W07 preflight with both budgets, through `workstation/v14_cost.py` (W08), on
2026-11-12. It replaces the 2026-11-12 estimate. Bedrock prices: Sonnet 4.6 Regional, 3.3 USD per 1M input tokens and
16.5 USD per 1M output tokens.

**Calls.** 45 Converse calls: 10 expectations × 3 samples plus 3 criteria × 5 samples. Throttled calls are retried, up
to 6 times (V14-OP5). R15 met two throttles (F-R15-1). A retried call is billed again only if it returned.

| Item | Planned | Upper bound | Basis |
|---|---|---|---|
| Bedrock input | 592,378 tokens, 1.95 USD | 947,804 tokens, 3.13 USD | Measured packs (63,965 tokens) and criterion inputs (34,168, 11,895, 26,340) over their samples, plus the rehearsal's measured overhead per call. Upper adds 20% for retries and malformed answers |
| Bedrock output | 45,000 tokens, 0.74 USD | 110,592 tokens, 1.82 USD | `maxTokens` 2048: 45 × 2,048, plus 20% |
| **Bedrock, measured** | **2.70 USD** | **4.95 USD** | `v14_cost.py` |
| Host running | 2 sittings × 2 h: 0.62 USD | 3 sittings × 3 h: 1.39 USD | 0.154686 USD per running hour |
| Host stopped (V14-D1) | 3 days: 4.60 USD | 7 days: 10.74 USD | 0.063916 USD per stopped hour |
| Snapshot (V14-OP7) | at most 0.40 USD per month | about 1.9 USD to 2027-03-31 | 8 GB at most, at 0.05 USD per GB-month (Assumed: not read for eu-north-1). An incremental snapshot of the used blocks is smaller |
| **V14** | **about 8.3 USD** | **about 19 USD** | Budget 10 USD per month; credits 199.19 USD at R15 step 01 |

The planned Bedrock figure is now measured, not assumed. The hours and days remain the operator's pace. At the upper
bound the 85% and 100% budget alerts fire. The credits cover it.

**The go asked for** (STEPS.md, the STOP after H02): hourly charges from H03 until H11d, the 45-call pass at H06, and
points P1–P4. The go is recorded here before H03.

### The go (operator, 2026-11-13, in session)

Given for hourly charges from H03 until the H11d teardown, and for the 45-call pass at H06.

- **P1.** As written: `eu.anthropic.claude-sonnet-4-6`, version tag `bedrock-converse-eu-north-1@<run date, UTC>`.
- **P2.** `processing_route.authority`, in the operator's words: "The operator authorises processing of the Part B
  text of the 2025 submission by eu.anthropic.claude-sonnet-4-6 over Bedrock Converse (EU geographic profile,
  private endpoint, invocation logging off) for the V14 blind assessment. This is the operator’s own decision of
  2026-11-13, recorded with V14-OP1 to OP9. No consent of any other party is recorded." `processing` and `export`
  as drafted. The wording is in `host/v14_h05b_receipt.sh`.
- **P3.** As written: Run Command timeout 7,200 s; resume from the checkpoint.
- **P4.** As written. Sitting 1: H02, H03 to H06, then H07 stop. Sitting 2: H08 to H09, then H07. Sitting 3 only
  for route (ii).
- **V14-D2** accepted.
