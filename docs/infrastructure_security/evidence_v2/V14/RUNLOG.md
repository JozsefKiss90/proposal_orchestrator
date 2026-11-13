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
| 2026-11-13 | operator | Sitting 1 started. H03 PASS: `path=create`, change set 7 Add, `c7i-flex.large`; **create executed 00:01:24Z** (hourly charges from here), `CREATE_COMPLETE`, host `Online` on try 0, end 00:03:15Z. H04a–d PASS: tarball sha256 `9c5351ef…132a`, 92,413,570 bytes, equal to O5; install 299 files, 17 sums; verify all 11 checks true, manifest `04f8218f…19dd`, revision `17e32d54`, Bedrock runtime on a private address, no internet route; inbound input sha256 matches, 19 members (8/1/10, 1 manifest, 0 ESR), in-app equal 8, root mode 700, local archive removed. H04e not yet run |
| 2026-11-13 | agent | H05a and H05b refused by the sender before sending: non-ASCII characters (`§` in header comments; the `’` of the P2 wording). Nothing ran on the host. Fixed in all five scripts carrying them (H05a, H05b, H06, H08, status): `§` written as "section", the apostrophe as the Python escape `’`, so the receipt value is unchanged. The rehearsal had run the scripts directly, not through the sender. H05b re-run on the simulated host: green |
| 2026-11-13 | operator | H04e PASS: one `delete_exit=0`; then versions 0, markers 0 (V14-OP1 holds). H05a PASS: one import manifest; preflight exit 1 with 2 flags (`other`, `word scan`: V14-F8); pack set `sha256:fe975e4b8489`, equal to W07; package complete under 400000, 10 packs; no checkpoint yet; assessor version `bedrock-converse-eu-north-1@2026-11-13`, revision `17e32d54`; rendered request `eu.anthropic.claude-sonnet-4-6`, temperature 0.0, `maxTokens` 2048, no tool configuration, `eu-north-1`; draft `38b9c10c…aed6`. H05b PASS: no placeholders left; receipt `75eb46f0…fa91`, mode 600; check exit 0, `receipt check: green`. Next: H06 |
| 2026-11-13 | operator | H06 PASS, checked against the PASS row as corrected by V14-F9. Window 08:12:01Z to 08:18:49Z (assess 08:12:07Z to 08:18:37Z, 6.5 minutes). Receipt green before; assess exit 0; one report `blind_96a09b983831_0001.json`, sha256 `f5c99a91…24bd`; one candidate; 46 live calls, 0 replayed, 1 discarded draw (V14-F9); 46 requests; no tool configuration, no child process; `maxTokens` 2048, temperature 0.0; no unscored criterion; checkpoint 48 lines. Freeze exit 0, 22 of 22 checks; baseline `blind_baseline_f5c99a91adc9.json` (equal to the report) and its `.freeze.json` `307d93fe…1add`. Receipt green after, against the report |
| 2026-11-13 | agent | At the operator's request: `host/v14_h08c_skeleton.sh` (step H08c-0) builds the skeleton of `dispositions_first.json`: schema 1.2, the template's 29 ids (equal to the ESR record's, in order), the header bound to the ESR record `5c9b9c8e…` and to the H06 baseline, judgement fields empty, no template text carried over; metadata out only. Rehearsed (R33). H08a written out as one block. The operator runs H08a, H08b, H10a and H07 stop now; H08c is its own sitting |
| 2026-11-13 | operator | Sitting 1 end, all checked by script. H08a PASS: pack `kind=esr`, archive `fb7b31e6…5823`, 6,074 bytes, member `5c9b9c8e…b0a9`; upload sha and size match, `cp_exit=0`, `aws:kms` with the project key, bucket key on; inbound 09:58:41Z `archive_sha256_matches=yes`, 1 member, none refused, `esr_present_before=no`, local archive removed; delete then versions 0, markers 0. H08b PASS (10:12:29Z): `esr_present=yes`, `audit_exit=1` (168 advisory flags), 1 audit report `integrity_96a09b983831_0001.json` (`fa24f1e1…e05c0`), `baseline_bound=bound`. H08c-0 PASS (10:15:38Z): template `90484fcb…a9ef` schema 1.2, 29 ids equal to the ESR record's in order; one freeze record; baseline `f5c99a91…24bd`, copy matches; skeleton `9cc17437…d954`, mode 600, 29 rows, loads; judgement fields empty. H10a PASS: 46 Converse events between 08:12:11Z and 08:18:37Z, all `AssumedRole` as the runtime role on the H03 instance, all through the H03 Bedrock runtime endpoint, all `eu.anthropic.claude-sonnet-4-6` in `eu-north-1`, `errorCode` null (46 = 45 + 1 discarded draw, V14-F9). H07 stop1 PASS: stopped at 10:17:00Z after 10 h 16 min running (about 1.59 USD of host time at 0.154686 USD per hour); endpoints and the 8 GB volume remain at 0.063916 USD per hour. The pack checker's first line reads `kind=esr tag=…` on one line; checked by eye. Next: the H08c sitting (H07 start2, H08c, H08d, H10b) |
| 2026-11-13 | operator | Sitting 2 started. H07 start2 PASS, checked by script: `path=resume`, stack `CREATE_COMPLETE`, instance `stopped` before, start 10:30:43Z, end 10:31:23Z, host `Online`; outputs equal to H03's (hourly charges again from 10:30:43Z) |
| 2026-11-13 | operator | H08c done in the interactive session, as the operator reports it; no evidence file yet (H08d lists the files). First comparison `comparison_f5c99a91adc9_0001.json`, sha256 `d24dd56d…08ea`: 16 of 29 observations detected, 13 misses; 5 of 15 criticisms detected (0.33); contested strengths 0. Its dispositions: 11 rows read by the operator, 18 drafted by rule. Successor `dispositions_second.json` supersedes the first: all 29 rows `operator_confirmed`, header `operator_reviewed`. From it: `comparison_f5c99a91adc9_0002.json`, `operator_review_06fd1a7d5919_0001.md` (`eba8d44d…abe3`) and `operator_decisions_06fd1a7d5919_0001.md` (`8de0425a…0c7e`). Limitation V14-L2 and deviation V14-D3 recorded (below). One false positive recorded by the operator: the implementation criterion, a shortcoming present in 5 of 5 samples, cause rubric interpretation. The hashes of the host files did not reach the agent; H08d lists them |
| 2026-11-13 | operator | First send of H08d, H09 and H07 stop2 at 16:50Z refused before any AWS change: the workstation session had expired (`V14_H08d_status1.json` and `V14_H09_return.json` `NotSent`; `V14_H07_stop2_log.txt` `RESULT=refused-account`). Nothing ran on the host. Rerun after `aws login` with the suffix `_fix1` |
| 2026-11-13 | operator | Sitting 2 end, checked by script. **H08d PASS** (`V14_H08d_status1_fix1.json`, 16:52:40Z): `root_mode=700`, 37 files by path, size and sha256 only. Comparisons `…_0001` `d24dd56d…08ea` and `…_0002` `06fd1a7d…b796`, two `revisions_` files, `review_diff_06fd1a7d5919_0001` (.json, .md); four review files, the two `06fd1a7d5919` hashes equal to those in V14-D3 and a pair for the first comparison (`d24dd56dbcbe`); `count_diffs=0`. `esr_work` holds 12 files: `dispositions_first.json` `2eba3178…313f` (filled, no longer the skeleton), its two equal backups `bd0c15b7…c821`, `dispositions_second.json` `ed323756…052b`, `notes_first.json`, `notes_second.json`, and the operator's working files `h.py`, `digest.txt`, `match.txt`, `match_all.txt`, `false_positives.txt`, `todo.txt`; all stay on the host. Baseline, report, audit and register hashes unchanged. **H09 PASS** (`V14_H09_return_fix1.json`, 16:52:57Z): `reports=1`, `report_sha256` equal to H06's, key=value lines only, no prose; `live_calls=46`, `discarded_draws=1` (on the implementation criterion); cells 10, covered 9 (`imp-magnitude` not covered, 0.55); criteria excellence 4.1 (spread 0.1), impact 3.8 (0.0), implementation 4.1 (0.0); total 80.2 of 100, overall and individual thresholds met. **H07 stop2 PASS** (`_fix1`): stopped at 16:53:50Z after 6 h 23 min running (about 0.99 USD of host time); volume `in-use`, 8 GB. **H10b** (`V14_H10b_start-session.json`, 7 events): 4 sessions by the operator's role at 10:31:33Z, 10:32:15Z, 12:05:58Z and 15:37:45Z, each `target` the H03 instance, `documentName` null, no error; PASS once the operator confirms 4 sessions. 3 more events, see V14-F10 |
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
- **Limitation V14-L2 (operator, 2026-11-13, accepted and recorded at the operator's request).** In
  `dispositions_second.json` the 13 misses carry `failure_mode: undetermined`, quotes selected by script, and status
  `Assumed`. V14-OP9 had them stand `Inferred`; the operator declares `Assumed` instead. The 5 detected criticisms
  carry quotes selected by script. No row was declared `Confirmed` by route (ii).
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

- **V14-D3. Two review files left the host (operator decision, 2026-11-13).** The operator copied
  `operator_review_06fd1a7d5919_0001.md` (sha256 `eba8d44d69d85a63b477dbc81d803f4e1466f4152248a22831e536ea99beabe3`)
  and `operator_decisions_06fd1a7d5919_0001.md` (sha256
  `8de0425a1a7033aa8bd9ceeae9798bfe4fc5005cda36dca59d16ecddce380c7e`) to a private folder on the operator's
  workstation, through the interactive session as gzip + base64 terminal output. The sha256 matched on both sides.
  This departs from V14-OP2, V14-OP4 and the receipt's `processing_route.export` for these two files. The same
  terminal output was pasted twice, on 2026-11-13, into a separate assistant chat; the operator states it was not
  decoded there. That chat is a processor outside the P2 authority, which names Bedrock Converse only. Nothing went
  to the repository, and the agent has not seen the content. The receipt is not edited: it records the route as
  declared before the run.

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
  confirmed at H06 on 2026-11-13: assess and freeze ran green after this flagged preflight).
  - **Tables: 250 rows rendered and parsed, against 275 in the import manifest.** The operator explains the gap of
    25 by the 25 rows on pages 1–4, which lie outside the declared page map (operator, 2026-11-12). The map is the original's configuration, so these rows are outside the assessed sections by
    declaration, not lost by the extraction.
  - **Word scan: 111 hits.** The scan is the instance-one leak scan (`harness/evidence_preflight.py`), built to
    keep instance-one names out of a sanitised tree. Here it runs over the private, unsanitised root of the real
    original, so hits are expected and do not indicate a leak into the assessment. Only the count is recorded.
    The preflight report lists up to 50 hits by path, line and noun, so it stays private: H09 returns no
    preflight report, only its whitelisted metadata.
- **V14-F9. The pass made 46 requests, not 45: one draw was malformed and drawn again.** H06 reports
  `live_calls=46`, `discarded_draws=1`, `requests=46`. The judge discards a response that does not parse and draws
  again; the report names each discarded draw on its cell or criterion score, with the parser's reason and the
  thrown text's sha256 and length (`harness/judge.py` `DiscardedDraw`). The freeze accepted the report (22 of 22).
  The H06 PASS row had asked for exactly 45; it now reads 45 plus `discarded_draws`. H09 shows which cell or
  criterion carries the redraw, as a count. Cost: one more call, about 0.06 USD at the planned rate.
- **V14-F10. The host itself tried to start Session Manager sessions, and was refused.** H10b shows three
  `StartSession` calls at 16:24:01Z, 16:24:27Z and 16:26:40Z by the runtime role on the H03 instance, each
  `AccessDenied`, with no target recorded. They came from a command run on the host, during the operator's fourth
  session. The role has no `ssm:StartSession`, so the refusal is the designed outcome, and no session opened. The
  operator to state what ran.

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
