# Handoff — overhaul, 2026-11-05 → 2026-11-09: Step 3 closed, wave 1 ready to implement

Written 2026-11-09 ~21:20 (Europe/Budapest). Repo `C:\Code\proposal_demo\proposal_orchestrator`, branch
`harness_overhaul` @ **`b7c2b9f9`** ("Record the 2026-11-09 declaration-draft re-render"). Working tree
clean. **This commit is the base commit for every wave-1 session.**

**Start here next session:** §4 (what to do, in order). Every ticket file carries its own session brief.

## 1. Status report

| Plan step | State | Evidence |
|-----------|-------|----------|
| Step 0, baseline | **done**. Windows full suite: 9,237 passed / 43 failed / 87 skipped, 900 s; the 43 failures by node id are the red line | `plans/overhaul/BASELINE.md` §4, raw `plans/overhaul/baseline-windows.txt` |
| Step 0, `.env.harness` | untracked and ignored (`83c210e9`, `09baceac`); **key rotation unconfirmed** | — |
| Step 0, worktrees | **`git worktree prune` not run** (prunable entries remain); `..\ur_slices` still exists | §5 |
| Step 1 (F1, F2) | not done; deferred to after the freeze | `discovery/scope-cut-2026-11-06.md` |
| Step 2, discovery | **done**: harness + runtime reviews (01–09), ultrareview slice 1 (10 findings) and slice 2 (10 findings), F7 wayfinder map with **all six tickets resolved** | `discovery/ultrareview-*.md`, `../overhaul-2026-11-f7-wayfinder/map.md` + `W01/W02/W03-findings.md` |
| Step 2, slice 3 (ESR side) | **not reviewed**. Free ultrareviews are used up and the operator won't buy credits; a free local `code-review` was agreed but not yet run | §5 |
| Step 3, scope cut | **closed 2026-11-06**: 7 tickets `ready-for-agent` (10–16); 01–09 deferred with reasons; wave-2 order recorded | `discovery/scope-cut-2026-11-06.md`, plan §4/§6 |
| PE-09 acceptance lane | **GREEN at `b7c2b9f9`**: 3,304 passed, 0 failed, 17 declared exclusions, exit 0 (operator's Windows run, 2026-11-09) | it was red at HEAD from drifted declaration drafts (W03 §5.1); fixed by the re-render (`a9331086`) + record `docs/tier4_orchestration_state/decision_log/msca-dn-declaration-draft-rerender_2026-11-09.json` (`b7c2b9f9`) |
| Step 4, implementation | **not started**: no ticket branch or worktree exists | — |

## 2. Decisions taken in these sessions (all recorded in the files named)

| Topic | Decision | Where |
|-------|----------|-------|
| DN run transport | **Bedrock Converse on the private eu-north-1 host**; `claude-cli` not used for private content | W05 Q0 |
| Locked revision | **One offline bundle from the freeze commit serves both V14 and V16; nothing lands between them.** A mid-way fix only if it blocks a run; if it changes assessment output, re-run V14 or mark the reports non-comparable | W05 Q1 |
| AN12 host steps | criteria 1 (install) and 3 (synthetic Converse freeze + receipt) only; criterion 2 and AN12 stay open | W05 Q2 |
| AN chain | AN15 does not ride in V14; AN12a not must-land; chain deferred past the deadline | W04 |
| V16 vs V14's gap | prose caveat in the operator's review only; no harness support | W06 |
| Stage B profile | sourced via the V09 index (all 2026 hashes match), not in the profile file; confirm with one operator applicability record; no code | W02 |
| Deadline | **24 Nov 2026** (WP 2026–2027 p. 12), not 23 Nov | W02 |
| Ticket 01 | deferred until after V16 (the only output-changing candidate); finding 5 moved into 15 | cut Q1 |
| Ticket 03 | off route: its misroute does not reach the blind assessment; 12 covers the omitted `--transport` | W03 §3, cut |
| Freeze date (2026-11-09) | **Tue 10 is not strict.** Freeze when 11 and 10 have landed plus whatever of 12–16 is done, **at the latest Thu 12**. Each day later shifts R11 → AN12 → V14 by a day; V16 (~19–20 Nov) is the date that matters | this session |

## 3. Order (operator-approved 2026-11-09)

Numbers record when a ticket was written, not its priority: 01–09 came from the 3–4 Nov reviews, and 10–16
were written at the cut in execution order. All under `.scratch/overhaul-2026-11/issues/`.

| Order | Ticket | Why here | Parallel with |
|-------|--------|----------|---------------|
| 1 | **11** declare the 2026 resubmission in the importer (W-1) | the only true must-land: V16 cannot import its candidate without it; ~60–80 lines; not rule 5 | 10 |
| 1 | **10** the acceptance lane is GREEN only when proven (UR-D) | every other ticket's "done" cites lane green, which can currently be faked; ~100–180 lines | 11 |
| 3 | **12** refuse a bad configuration before the first assessor call (UR-A) | biggest time/cost risk in V14: a paid Converse run crashing mid-way | 13, 14 |
| 4 | **15** a resume is honest (UR-B + finding 5) | V14 needs `--resume`; **after 12** (same command module) | 16 |
| 5 | **14** the integrity audit keeps every DC project (UR-E) | audit correctness for both runs | 12, 13 |
| 6 | **13** receipt guard anchored on this repository (UR-C) | tiny privacy guard | 12, 14 |
| 7 | **16** two refusals (UR-F) | tiny; both cases already avoided by the runbook's explicit flags | 15 |

Blocking edges as written in the tickets: 12, 13, 14, 16 ← 10; 15 ← 10, 12; 11 and 10 have none.
Wave 2 (01–09, from ~25 Nov): see `discovery/scope-cut-2026-11-06.md`, "Implementation order".

## 4. What the next session does, in order

1. **Read:** this file, `discovery/scope-cut-2026-11-06.md`, the ticket, `plans/overhaul/BASELINE.md` §4,
   `CLAUDE.md` §16–17, `CONTEXT-MAP.md` (+ both CONTEXT files), `docs/agents/*.md`.
2. **One worktree per parallel ticket**, from `b7c2b9f9`, never sharing the main tree:
   ```powershell
   git worktree add -b ticket/11-resubmission-2026 ..\wt_11 b7c2b9f9
   git worktree add -b ticket/10-lane-proven ..\wt_10 b7c2b9f9
   ```
   Merge back into `harness_overhaul` in the §3 order. Later tickets base on the commit after their
   blockers merged (their briefs say which).
3. **Ticket 11's first step is the operator's:** confirm the four identity names (proposal:
   `resubmission_2026` / `msca-dn-2026-resubmission` / `MSCA-DN-2026_part_b_resubmission`, title naming
   HORIZON-MSCA-2026-DN-01). It also writes a decision-log entry for the new identity (§9.4).
4. **Each ticket session** follows its brief: `diagnosing-bugs` first where it fixes a defect, then `tdd`
   (failing tests first, in the listed order), then `code-review` since the base commit. Done when:
   - the acceptance boxes are ticked;
   - the targeted tests and the full suite show **no new failure by node id against BASELINE.md §4's 43**;
   - for 12–16, the PE-09 lane is green, run with ticket 10's lane once it has merged.
   Set `Status: done` (or the tracker's done string) and add a `## Comments` line with the merge commit.
5. **Until ticket 10 merges,** run every lane with a new `--junit` path, never `-k`, `--area` or
   `--from-junit`, and read pytest's exit code yourself:
   `py -3.10 -m harness.commands.acceptance_lane --junit $HOME\lane-<date>-<n>.xml; echo "exit=$LASTEXITCODE"`
6. **Freeze:** when 11 + 10 (+ whatever of 12–16 is done) have merged, and by Thu 12 at the latest:
   - run the full suite against §4;
   - run one lane;
   - merge to `msca-dn-pre-eval`;
   - tag the freeze commit;
   - build the AN12 offline bundle from it (`plans/msca_dn_an12_host_runbook.md`, Part 1).

   Then R11, then AN12 criteria 1 and 3, then V14 (W05 Q3). Any of 12–16 not merged by then waits until after V16.
7. **Docs and records that may follow the freeze** (they change no bundled behaviour):
   - the PE-09 runbook's Converse delta: V14/V16 command lines, the `bedrock-converse-eu-north-1@<date>`
     version-tag rule, the receipt section, and the stage-B `--document` id from ticket 11;
   - the Stage B profile-applicability record (W02 §"smallest action");
   - the ledger edit relaxing V16's blocker from V15 to V14.

## 5. Open items outside the tickets

- **Slice 3 review** (ESR side: `esr_comparison`, `operator_review`, `comparison_diff`, `deferral_register`
  + command, `authority_matrix` + command): a free local `code-review`, review only. A finding gets a ticket
  only if it would make V14's ESR comparison wrong or crash. Run it **before the freeze**, because V14 uses
  that code after it.
- **Operator housekeeping:**
  - rotate the transport key;
  - run `git worktree prune` **from Windows** (the Linux shell cannot see the `C:/` paths);
  - `git worktree remove ..\ur_slices`;
  - close draft PRs #1–#3 without merging and delete the `ur/*` branches locally and on `origin`.
- **Plan §6, still open:** which branch becomes the long-lived base after the freeze (proposal: merge
  `msca-dn-pre-eval` → `main` and archive the rest by tag).
- **Before wave 2:** record the post-wave-1 full suite as `BASELINE.md` §5. Ticket 08's area holds 4 of the
  baseline failures; characterise them first.

## 6. Things that will trip a session

- **Two baselines exist.** §4 (Windows, 43 failures) is binding. §1–3 is a Linux cross-check with
  sandbox-only failures; don't use it as the red line.
- **`tests/test_transport_openai_compatible.py`** fails 10 tests on Windows because they reach the network
  (`example.com`) instead of a mock. They're in §4; a ticket touching `runner/transport/` must not read them
  as its own regressions.
- **Declaration drafts are coupled to the tree.** Any committed file under `docs/`, `workspaces/` or
  `plans/` that names a fidelity register by path or hash makes the drafts stale and turns the lane red. Fix:
  run `py -3.10 -m tools.draft_fidelity_declarations`, then write a successor
  `msca-dn-declaration-draft-rerender_<date>.json` with before/after hashes. That record must name no
  register path or hash. Run `tests/test_msca_dn_declaration_drafts.py` **in full**, not just the
  reproducibility class (the 2026-11-06 re-render missed the record test that way).
- **Agent sandbox (Linux VM on the operator's machine):**
  - it cannot delete in the connected folder without operator approval, so atomic writes leave `*.tmp`
    files and fail;
  - background processes die when a call ends;
  - each call is limited to 3 min, and tests over the folder mount are slow;
  - Linux `git status` shows every file "modified" after a remount; that is CRLF noise, so use
    `git -c core.fileMode=false diff --ignore-cr-at-eol`.

  Run suites and lanes on Windows.
- **`gh` is not installed.** Create PRs from the GitHub compare page.
