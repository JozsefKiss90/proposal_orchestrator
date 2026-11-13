# Handoff — 2026-11-11: three plans in reliability order (overhaul · AWS · historical validation)

Written 2026-11-11 (Europe/Budapest). Repo `C:\Code\proposal_demo\proposal_orchestrator`.
Supersedes the calendar in `handoff-session-2026-11-09.md` §3–§4 and W05 Q1–Q3. Dates no longer drive
the order: **every change on the V14/V16 run path lands first, the host is fully evidenced, the code is
frozen once, then the runs.**

**Start here next session:** §4, step 0. Each step names its plan, its ticket, who acts and its protocol (§3).

## 1. State at handoff

| Item | Value |
|------|-------|
| `harness_overhaul` | `ad0900a4` ("Close F3: transport key revoked …"); wave 1 (tickets 10–16) merged and closed |
| `msca-dn-pre-eval` | `6b1c2658`, tree identical to `harness_overhaul` at `dbf6582f` |
| Tag | `msca-dn-freeze-2026-11-11` → `6b1c2658`. **Superseded** by the re-freeze in step O5; keep it as history, never build a bundle from it |
| Last full suite | at `96f40333`: the 42 node ids of BASELINE §4 minus the drafts-reproducibility case, plus 2 fixed test-only at `1ab64dc2` |
| Last lane | GREEN at `dbf6582f`: 3,532 passed, 17 declared exclusions, exit 0 |
| Transport key | revoked (F3, `ad0900a4`, `docs/tier4_orchestration_state/decision_log/transport-key-revoked_2026-11-11.json`) |
| AWS done | E0, R0–R10, R12a, R16 (DC-38 deferred per OD12) — worklog `docs/infrastructure_security/aws_hardening_worklog_v2.md` |
| Historical done | V01–V13, V17, V18 (V02c criterion 1 excluded by declaration) |
| Stray files | `ad0900a4` re-committed `.scratch/overhaul-2026-11/suite-merged-2026-11-10{,b,c}.txt`; untrack them in step 0 |

## 2. Decisions taken 2026-11-11 (operator, in session) — record them in step 0 (§9.4)

1. **Anonymisation is out of scope.** The original is assessed privately on the AWS host, so no derivative
   is needed. Out: AN12 criterion 2 (A0–A7 pipeline), AN12a, AN13, AN14, AN15, AN-P, and the AN8b
   threshold question. **Kept, because the runs use them:** AN1a (Converse backend), AN1b (Converse
   receipt), AN1c (judge independence on shared Bedrock), and AN12's code — `runner/offline_bundle.py`,
   `harness/commands/converse_smoke.py` — which is the only route for code onto a host without internet.
2. **Reliability order replaces the deadline order** (W05 Q1–Q3): wave-2 harness chain and a new
   wording ticket (17) land before the runs; R12b and R14 precede R15; one re-freeze; one bundle for V14
   and V16; nothing lands in that bundle between them (W05's locked-revision rule stays).
3. **R15 is rescoped** to "host install and Converse smoke run": offline install +
   `verify --probe-no-internet` + the synthetic Converse blind pass with a validated receipt. Its R12b
   blocker stays.
4. **V15 stays V16's blocker.** The planned ledger edit relaxing V16 to V14 is dropped.
5. **Ticket 11's register sentences and slice 3's F1 are fixed before the runs** (ticket 17), which
   resolves the Unresolved gap in `msca-dn-resubmission-2026-identity_2026-11-10.json`.

## 3. The three protocols (follow them; they are binding)

**Overhaul** — `docs/agents/issue-tracker.md`; tickets in `.scratch/overhaul-2026-11/issues/`.
- One session per ticket, in its own worktree from the merge commit named in §4, never the main tree:
  `git worktree add -b ticket/<NN>-<slug> ..\wt_<NN> <base>` then
  `robocopy .claude\runs ..\wt_<NN>\.claude\runs /E /NFL /NDL /NJH /NJS` (without it 8 dev_graph tests fail
  and rewrite committed Tier 4 files).
- The ticket's own session brief governs (skills: `diagnosing-bugs` for a defect, then `tdd`, then
  `code-review` since the base). Tell the session its base commit; the briefs' placeholders are stale.
- **Targeted tests only in the session — and they must include every module that imports a changed
  module** (wave-1 lesson: ticket 16 broke two integrity-audit tests nobody ran). No full suite, no lane.
- Before committing: `git diff --stat <base>` lists only the ticket's files (no
  `docs/tier4_orchestration_state/dev_graph/` rewrites, no run outputs) and includes the ticket file
  with its boxes ticked except "lane green" and "full suite".
- The operator merges a batch (`git merge --no-ff`), then runs once in the main tree:
  `py -3.10 -m pytest -q -rf 2>&1 | Tee-Object -FilePath .scratch\overhaul-2026-11\suite-<tag>.txt`
  (leave it untracked) and `py -3.10 -m harness.commands.acceptance_lane --junit $HOME\lane-<tag>.xml; echo "exit=$LASTEXITCODE"`.
  The agent compares failures **by node id** against the current BASELINE section; the lane must print
  GREEN with exit 0. Then the agent sets `Status: done` and appends a `## Comments` line with the merge
  commit and that evidence.
- A commit naming a fidelity register by path or hash under `docs/`, `workspaces/` or `plans/` turns the
  lane red; fix per `handoff-session-2026-11-09.md` §6.

**AWS** — `plans/aws_redeployment_tickets.md` + `plans/aws_redeployment_handoff_2026-10-21.md` §7 and §7a.
- The operator performs every AWS step. The agent writes
  `docs/infrastructure_security/evidence_v2/<R>/STEPS.md` (exact commands, PowerShell and CloudShell
  forms, evidence file per step, PASS criterion per file), the operator runs it and saves
  `<R>_<NN>_<name>.<json|txt|png>`, `RUNLOG.md` and `<R>_outputs.json`; the agent writes `VERIFICATION.md`.
- Ticked only when every criterion is PASS (or N/A with reason), register v2 rows are updated, a
  worklog-v2 entry exists, and the operator confirms in session. A FAIL gets `STEPS_fix1.md`; evidence is
  never edited.
- Never in evidence: secrets, keys, tokens, prompt or proposal text, model output beyond a fixed test
  string. The agent greps for `AKIA`, `aws_secret`, `SecretString`, `SessionToken` and refuses on a hit.
- IDs come from `<R>_outputs.json`, never memory. No IGW/NAT/`0.0.0.0/0`, invocation logging off.
  **R11 is the first hourly cost and needs the operator's explicit go.**

**Historical validation** — `plans/msca_dn_historical_validation_tickets.md` ("Shared constraints") +
`plans/msca_dn_pe09_runbook.md`.
- V14 is the operator's: Claude does not run the private assessment, transmit proposal content or spend
  quota on it; it prepares records and verifies the bindings the operator deposits.
- V15: Claude drafts, the operator signs; nothing is ticked without closure evidence.
- Immutable public artifacts (74.60 baseline, approved dispositions/comparison, registers, ESR record) are
  never edited; new results are successor records. Honest status vocabulary. Read command help before
  documenting a command; never invent a flag.

## 4. The order

Three lanes run in parallel until the re-freeze; then one sequence.

```
step 0 ─┬─ Overhaul O1 → O2 → O3 → O4 ─┐
        ├─ AWS      A1 → A2 → A3 ──────┼─ O5 re-freeze → A4 → H2 → H3 → H4 → H5 ─→ O6, A5
        └─ Historical H1 ──────────────┘
```

### Step 0 — records (agent writes, operator approves, one commit on `harness_overhaul`)
- `git rm --cached .scratch/overhaul-2026-11/suite-merged-2026-11-10*.txt` (keep the files on disk).
- Decision-log entry `docs/tier4_orchestration_state/decision_log/plan-order-reliability_2026-11-11.json`
  recording §2 items 1–5, each with prior rule, new rule, reason, impacted tickets.
- Mark the out-of-scope AN tickets in `.scratch/msca-dn-anonymisation/tickets.md` (`wontfix`, citing the entry).
- Amend R15's text in `plans/aws_redeployment_tickets.md` to the rescoped criteria (operator approves in session).
- `plans/overhaul/BASELINE.md` §5: the post-wave-1 red line = §4's 43 minus
  `tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible`
  (42 node ids), evidence `suite-merged-2026-11-10c.txt` + lane at `dbf6582f`. Wave-2 briefs read "at or above §5".
- Write **ticket 17** (`17-submitted-not-yet-evaluated-wording.md`, `Status: ready-for-agent`, with a session
  brief): wording keyed on the register's `is_submitted_document` and on whether an ESR evaluated the text —
  the V18 register sentences ("This file is the text the ESR evaluated", "The ESR evaluated this text",
  ids under `historical_submission`) for a not-yet-evaluated document; `esr_comparison._SCORE_STATEMENT`
  and each row's `historical_proposal_evidence.note`; `operator_review` inventory notes and the
  "earlier sanitised copy" heading. Committed sanitised comparisons and reviews must replay byte-equal.
  Source: `discovery/slice3-esr-review-2026-11-10.md` F1 and the identity record's R-gap.

### Overhaul lane (base = `harness_overhaul` after step 0)
- **O1:** 01 ∥ 04 ∥ 17. Before merging, `git diff --name-only` the three branches against each other; merge
  a shared-file pair sequentially. Merge order 01, 04, 17 → suite + lane.
- **O2:** 03 (← 01) ∥ 05 (← 04) → merge → suite + lane.
- **O3:** 02 (← 01, 03) ∥ 06 (← 05, 01) → merge → suite + lane. 06 edits the blind-report module; 02 and
  03 share rubric grading — that is why those edges exist.
- **O4:** nothing else lands before the freeze. The runtime chain (07a, 07b, 08, 09) is off the run path
  and 09 rewrites the transport seam the runs use, so it waits for O6.
- **O5 — re-freeze** (after O3 and H1): full suite against §5 and one lane on `harness_overhaul`; then
  `git switch msca-dn-pre-eval; git merge --no-ff harness_overhaul`; check
  `git diff --stat harness_overhaul msca-dn-pre-eval` is empty; annotated tag `msca-dn-freeze-<date>`;
  `git worktree add --detach ..\freeze_bundle <tag>`; build per `plans/msca_dn_an12_host_runbook.md`
  Part 1 with downloads and output outside both checkouts; record the tarball sha256 in a decision-log entry.
  From here until V16 is done, nothing is built from `harness_overhaul`. A run-blocking defect is fixed on a
  branch from the tag; if the fix changes assessment output, V14 is re-run or the reports are marked
  non-comparable (W05 Q1).

### AWS lane
- **A1 — R11** endpoints and host (blocked by R4–R8, all done). Agent writes `evidence_v2/R11/STEPS.md`;
  operator gives the explicit go. Done: endpoints available, no public IP, Run Command `Success`, one
  Converse call over PrivateLink attributed to the runtime role with its boundary (F1), DC-01/02/04/05/14/26/37
  evidenced, stack deleted and recreated cleanly.
- **A2 — R12b** full re-evidence with the R12a collector: register v2 complete, **F7** (presigned PUT to an
  outside bucket refused from the host), DC-15 in-host tests, DC-33–35 via the R9 launcher, DC-40 re-assessed.
  The host carries no private content before this closes.
- **A3 — R14** start/stop/teardown scripts (PowerShell + CloudShell), weekly cost check with cited prices,
  OD10 upgrade checklist (operator-only). **If O5 is not near, tear the endpoints-and-host stack down with
  the R14 script and recreate it for A4.**
- **A4 — R15 (rescoped)**, after O5 and A2: AN12 runbook Part 2 on the new bundle — sha256 check, install,
  `runner.offline_bundle verify --probe-no-internet`, production-config verification (criterion 1), the
  synthetic Converse blind pass frozen with a green receipt (criterion 3). OD7 models, OD1 region, version tag
  naming `bedrock-converse` and the Region. Successor decision record to
  `msca-dn-an12-offline-bundle_2026-10-16.json`.
- **A5 — R13** documentation amendments, any time after A2; each amendment approved by the operator in
  session before it is applied.

### Historical lane
- **H1 — runbook Converse delta** (`plans/msca_dn_pe09_runbook.md`; docs only, before O5 so the bundle
  carries it): V14/V16 command lines on `--transport bedrock-converse` (ticket 12 refuses an omitted
  transport when the environment resolves to Converse); version tag `bedrock-converse-eu-north-1@<date>`;
  the receipt section (keep receipts outside every checkout — ticket 13); **resume = the original command
  line plus `--resume`, nothing else** (ticket 15 refuses a changed temperature or `max_tokens`); the
  Stage-B importer id `--document resubmission_2026` (ticket 11); where `fidelity_to_submitted_original`
  goes for Confirmed misses (slice 3 F2) and that audit references must spell the `--audit` path exactly
  (F3). Read each command's `--help` first.
- **H2 — V14** (operator, on the host, after A4): runbook §4–§6 — dry import, configuration, import,
  preflight, assess (checkpointed), freeze under V04 before any ESR material, then audit, compare, review.
  Claude verifies deposited bindings afterwards and drafts the diagnosis record skeleton; it never sees
  proposal text.
- **H3 — V15**: Claude drafts the acceptance record (hashes, profile version, code revision = the O5 tag,
  scope stated as content-focused, V11 rows resolved or carried with owners, revision backlog); the operator
  signs.
- **H4 — before V16**: human-approved revisions land in the authoritative 2026 text (runbook §7); the Stage B
  profile-applicability record (W02 "smallest action"; one operator record, no code).
- **H5 — V16** (operator, same bundle as V14): runbook §8 with the stage-B document, its own manifest,
  register, declarations, preflight, assessment, audit. No compare/review/diff (no 2026 ESR).

### After V16
- **O6:** 07a ∥ 08 (characterise ticket 08's 4 baseline failures first) → 07b → 09 (lane green, rule 5;
  keep `SKILL_MODEL`/`AGENT_MODEL` importable by `harness/judge.py`); then hygiene F1/F2; record
  BASELINE §6.
- **A5** if not yet done; R16 stays deferred unless OD12 changes.
- X01–X04 only when a claim needs them.

## 5. Things that will trip a session
- The Linux agent shell cannot delete in the connected folder (atomic writes leave `*.tmp`), shows CRLF noise
  in `git status` (use `git -c core.fileMode=false diff --ignore-cr-at-eol`), and cannot see `C:/` worktrees.
  Suites, lanes and worktree commands run on Windows.
- PowerShell 5 `Tee-Object` writes UTF-16; the agent decodes it when comparing node ids.
- `git worktree prune` from Windows: `wt_10`–`wt_16`, `_wt_head`, `e5f_eval_mock`, `ur_slices` and the
  `.claude/worktrees/e5f-…` entry are prunable; remove the ticket branches after their merges; close draft
  PRs #1–#3 and delete `ur/*` locally and on `origin`.
- `gh` is not installed; PRs go through the GitHub compare page.
- `harness_overhaul` and `msca-dn-pre-eval` are ahead of `origin`; push branches and tags when you want the
  freeze recoverable off this machine.

## 6. Progress log

Ticked only on the evidence each protocol (§3) names. Newest line last.

- [x] **Step 0** — `60fca14e`. Decision entry `plan-order-reliability_2026-11-11.json` (D1–D5, operator
      confirmed in session); AN tickets wontfix; R15 rescoped (operator approved); BASELINE §5 = 42 node
      ids, checked by node id against `suite-merged-2026-11-10c.txt`; ticket 17 written; suite outputs
      untracked and ignored. Guard tests run: 140 passed, 5 skipped.
- [x] **O1** — 01 ∥ 04 ∥ 17, merge 01 → 04 → 17, suite + lane. Merged by the operator: `df1b16cf` (01),
      `33d298f9` (04), `d5016542` (17). Suite at `2a8385d9`: 42 failed, 9,515 passed, 87 skipped. The 42
      failed node ids equal BASELINE §5 exactly (`suite-o1.txt`). Lane GREEN: 3,577 passed, 0 failed,
      17 declared exclusions (`lane-o1.xml`). 01, 04 and 17 are done. 04 closed on an operator exception:
      three `[:16]` slices in `operator_review.py` keep their width for byte-equal replay
      (`overhaul-04-display-width-exception_2026-11-11`).
- [x] **O2** — 03 ∥ 05, merge, suite + lane. Merged by the operator: `7f5c5cc3` (03), `c80732fc` (ESR
      successor bound to `msca-dn-2025-original`), `70fcb6b5` (05). Suite at `70fcb6b5`: 42 failed, 9,606
      passed, 87 skipped; the 42 failed node ids equal BASELINE §5 exactly (`suite-o2.txt`). Lane GREEN:
      3,645 passed, 0 failed, 17 declared exclusions (`lane-o2.xml`). 03 and 05 are done. 05 closed on an
      accepted gap: a comparison binds its revisions artifact by path only; a revisions hash is a format
      ticket after V16 (`overhaul-05-revisions-hash-gap_2026-11-11`).
- [x] **O3** — 02 ∥ 06, merge, suite + lane. Merged by the operator: `67224ced` (02), `7697524c` (06). Suite at
      `7697524c`: 43 failed; 42 equal BASELINE §5, the 43rd (`test_evidence_v2_tree_is_itself_clean`) came
      from the agent's R11 run log naming the secret patterns, fixed and re-run green. Lane GREEN: 3,746
      tests, 0 failed, 17 declared exclusions (`lane-o3.xml`). 02 and 06 are done. 06 closed on an accepted
      exception: the blind-baseline freeze keeps its fixed-name writer
      (`overhaul-06-freeze-writer-exception_2026-11-11`).
- [x] **H1** — runbook Converse delta. Merged by the operator as `2a8385d9`; covered by the O1 suite and
      lane above (the runbook guard is a lane module). The V14 compare line changes again when the ESR
      record is rebound off `msca-dn-2025-sanitised-v1` (operator, 2026-11-11: that intake is out of
      scope).
- [x] **A1** — R11 (operator's explicit go). Step sheet reviewed by the operator and merged as `34a4e2e1`;
      its tests pass (25). Round 1 (steps 01–05, read-only plus an unexecuted change set) run by the
      operator on 2026-11-11; every evidence file passes its criterion (`R11/RUNLOG.md`). The change set
      `r11-create-01` lists exactly the seven additions. Step 06 waits for the operator's explicit go;
      VERIFICATION.md follows step 23.
      DONE 2026-11-11 22:58 UTC: steps 06–23 PASS (host on `c7i-flex.large`, OD9-r1), operator confirmed R11 and
      reviewed R11-D11/D12 (`aws-redeployment-r11-host_2026-11-11`); last commit before close `17f4631d`.
- [x] **A2** — R12b. Confirmed 2026-11-12 01:14 UTC with F7 open (retest in the next host session, R12b-D9); register v2 35 VERIFIED_PASS / 4 DEFERRED / 2 N/A (`aws-redeployment-r12b-reevidence_2026-11-12`). Collector defects F-R12b-2–4 to fix before its next run. Step 12 done (346 passed, 1 skipped; guards CLEAN).
- [x] **A3** — R14. Confirmed 2026-11-12 with R14-D1 (offer-file prices) and R14-D5 (CloudShell steps 10–11 recovered) accepted; F7 closed (R12b criterion 2 ticked). Step 16: 224 passed, guards CLEAN. Both host creations deleted, nothing billable left (`aws-redeployment-r14-operations_2026-11-12`, `b25c7854`). F-R14-1/2 fixed; R15 runs the CloudShell teardown end to end and the input discard at a real terminal.
- [x] **O5** — re-freeze, tag, bundle, sha256 record. Suite at `3e66457c`: 42 failed, equal to BASELINE §5 by node id; lane GREEN, 3,729 passed, 17 declared exclusions, exit 0 (`suite-o5.txt`, `lane-o5.xml`). Merged into `msca-dn-pre-eval` with an identical tree; tag `msca-dn-freeze-2026-11-12` → `17e32d54`. Bundle from `../freeze_bundle`: sha256 `9c5351ef709905c391fd82d06ccdacf1a806c255350241c6d88a21b4d0f2132a`, 299 files, 16 wheels (`msca-dn-refreeze-o5_2026-11-12`). Nothing for V14/V16 is built from `harness_overhaul` from here.
- [x] **A4** — R15 (rescoped). Confirmed 2026-11-12. One host creation, 17:00:54–17:19:59 UTC, deleted, nothing billable left. Bundle sha256 equal to O5 on the host; verify 11/11; DC-33–35 VERIFIED_PASS (register v2: 38 / 1 DEFERRED / 2 N/A); the synthetic Converse pass froze with a green receipt; 26 CloudTrail events through the private endpoint. R15-D1–D4 accepted; R14-D5 and F-R14-2 closed. F-R15-1 (2 throttled calls, retried): check the Sonnet 4.6 quota and pacing before V14. Step 16: 289 passed, 1 skipped, guards CLEAN (`msca-dn-an12-host-run-r15_2026-11-12`).
- [x] **H2** — V14 (operator). Confirmed 2026-11-13. Blind original 80.2 against ESR 85.8; 16 of 29 detected, 5 of 15 criticisms; diagnosis record `ac7b8eb2…a065` on the host, counts in `evidence_v2/V14/DIAGNOSIS.md`. Limitations V14-L2, V14-F12 (to V15, owner the operator); deviations V14-D3, V14-D4; V14-F10 open. Host deleted 22:17:42Z; encrypted private snapshot kept to 2027-03-31 (re-dated after V16). H12 CLEAN.
- [ ] **H3** — V15 (operator signs)
- [ ] **H4** — revisions + Stage B profile-applicability record (operator)
- [ ] **H5** — V16 (operator)
- [ ] **O6** — 07a ∥ 08 → 07b → 09; hygiene F1/F2; BASELINE §6
- [ ] **A5** — R13
