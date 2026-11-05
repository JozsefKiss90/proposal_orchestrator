# Handoff — overhaul session of 2026-11-04 (runtime tickets, F7 wayfinder, ultrareview slice 1)

Written 2026-11-04 ~14:55 (Europe/Budapest). Repo `C:\Code\proposal_demo\proposal_orchestrator`, branch
`harness_overhaul` @ `09baceac` ("Ignore .env.harness (F3)"). Everything written this session is
**uncommitted** in the working tree (see §3). No code, tests or `CLAUDE.md` were changed.

**Start here next session:** `step3-scope-cut-plan.md` (this folder). It is the ordered to-do list that
closes Step 3.

## 1. What this session covered

1. **Runtime candidate tickets** (input: `handoff-runtime-candidates-2026-11-03.md`). Checked the handoff
   against the code at `5ba39e2d`, got the operator's decisions, and wrote tickets 07a, 07b, 08 and 09.
2. **Candidate E (retire cli-prompt / close the §17 TAPM banner)** went to the operator with corrected
   evidence. Decision: **not yet**.
3. **Wayfinder on F7.** Chart mode: destination and scope grilled with the operator, map plus six
   tickets written. No ticket resolved (the skill allows charting only in this session).
4. **Ultrareview.** Explained why it is needed and how to run it, re-scoped it into slices, and ran
   **slice 1** (free run 1 of 3). Triaged the 10 verified findings.
5. **Step 3 closing plan** written: merged candidate list, grill agenda, ultrareview commands for slices 2–3.

## 2. Decisions taken by the operator this session

| Topic | Decision |
|-------|----------|
| Ticket 07 size | Split into **07a** (parse/validate) and **07b** (write modes). For a **pure move pinned by characterisation tests written beforehand**, the ~400-line rule is measured on net-new/changed logic, not moved lines. |
| Ticket 08 scope | Covers **both** skill loops in `run_agent` (main and pre-gate). |
| Ticket 09 design | The ticket states one interface shape; the implementer runs design-it-twice first and the operator confirms. |
| Candidate E | **Not yet.** Keep the §17 banner; no E ticket; 09 keeps both prompt modes. |
| F7 map destination | A decided list of harness changes that must land by 10 Nov, so that the V16 run on the 2026 DN candidate before 23 Nov is frozen, audited, advisory, and states what it did not assess. |
| Stage A | **V14 before V16; V15 not required** (the ledger edge V16←V15 is to be relaxed to V16←V14 by a later operator action). |
| V16 venue | Private host, same Converse model and sample plan as V14; no anonymisation of the 2026 candidate. |
| Grounding scope | V16 declares grounding **unassessable**; X01 off the route. |
| F7 out of scope | PF eval lane (E5f, E5.1, E6–E9, calibration None-guard, E1.5 gold mislabels), X02, X03, X04. **In scope:** the AN chain (AN12a–AN15) and V02c. |
| Ultrareview scope | Three slices (run path, audit/records, ESR side); **anonymisation excluded entirely**. This answers plan §6 "Ultrareview scope". |

## 3. Files produced (all uncommitted)

| File | What it is |
|------|------------|
| `.scratch/overhaul-2026-11/issues/07a-skill-response-contract-parse-validate.md` | Runtime B part 1. `needs-triage`. No blocker. |
| `.scratch/overhaul-2026-11/issues/07b-skill-response-contract-write-modes.md` | Runtime B part 2: **four** write modes (single, multi, enrich, **payload**). Blocked by 07a. |
| `.scratch/overhaul-2026-11/issues/08-caller-context-one-module.md` | Runtime C. **Five** special cases at **two** sites (the pre-gate loop bypasses the guard). No blocker. |
| `.scratch/overhaul-2026-11/issues/09-one-model-invocation-module.md` | Runtime A. Blocked by 07a, 07b. PE-09 lane required. |
| `.scratch/overhaul-2026-11/discovery/decision-E-tapm-banner-2026-11-04.md` | Decision record for E, with evidence and the conditions to revisit. |
| `runner/CONTEXT.md` | **Modified:** glossary terms *Caller context* and *Skill response contract* (+12 lines). |
| `.scratch/overhaul-2026-11-f7-wayfinder/map.md` | Wayfinder map: destination, notes (charting decisions), fog, out of scope. |
| `.scratch/overhaul-2026-11-f7-wayfinder/issues/01…06-*.md` | W01 import route (research) · W02 profile applicability (research) · W03 run path and on-route tickets (research) · W04 does AN15 ride in V14 (grilling) · W05 V14 timing and locked revision (grilling; blocked by W03, W04) · W06 how V16 reads V14's gap (grilling; blocked by W05). All `Status: open`. |
| `.scratch/overhaul-2026-11/discovery/ultrareview-run-path-2026-11-04.md` | Slice 1: method, the 10 findings, triage, side finding, slices still to run. |
| `.scratch/overhaul-2026-11/step3-scope-cut-plan.md` | **Next-session entry point:** what's left before the grill, the merged candidate list with recommendations, grill agenda, after-grill steps, PowerShell commands for slices 2 and 3. |
| `.scratch/overhaul-2026-11/handoff-session-2026-11-04.md` | This file. |

Commit them together on `harness_overhaul` (e.g. "Runtime tickets 07–09, F7 wayfinder map, ultrareview slice 1, Step 3 plan").

## 4. Facts established that correct earlier documents

- **Catalog modes:** 27 skills, not 24. 24 declare `tapm`; **3 declare none and run in cli-prompt by
  default** (`milestone-consistency-check`, `budget-interface-validation` at n07, `decision-log-update`).
  cli-prompt is a live production path, not leftover code.
- **Phase E of `run_skill`** has four write modes, including `payload`, which writes `decision_log_entry` files.
- **Caller context:** five special cases at two sites; the pre-gate loop (`agent_runtime.py` ~1404–1418)
  never goes through the registry or the fail-closed guard.
- **PE-09 runbook** V14 commands use `--transport claude-cli` (V12 predates the Converse assessor AN1a).
  This conflicts with the map's Converse decision; W03 must settle it.
- `plans/overhaul/BASELINE.md` doesn't exist; 3 worktrees are prunable; Step 1 (F1/F2) is not started.

## 5. Ultrareview: how it actually works here (lessons)

- The repo's own skill `.claude/skills/code-review` **takes over** `/code-review`, so `/code-review ultra`
  runs the local review. Use the **subcommand** in a terminal: `claude ultrareview <PR#> --timeout 60`.
- There's no path filter, and the diff cap is ~8,000 lines / 500 files → review in slices.
- A branch review is refused ("Repo is too large") → use **PR mode**.
- Slice recipe: base branch = `msca-dn-pre-eval` with the slice files removed (or reverted to `main`);
  review branch = base + `git revert` of that commit; **draft PR whose base is the base branch** (GitHub's
  push link defaults to `main`, so change it). Check "Files changed" before running. A base *on top of*
  the reviewed branch gives an empty diff (the first attempt failed this way).
- Free runs: **2 of 3 left.** Leave `--post` off; findings go to the terminal and `~/ultrareview-*.txt`.

## 6. Live state outside the working tree

- **GitHub:** draft **PR #1** (`ur/review-run-path` → `ur/base-run-path`) is open. Branches
  `ur/base-run-path` and `ur/review-run-path` exist locally and on `origin`. Close PR #1 without merging and
  delete the `ur/*` branches once all slices are done.
- **`.env.harness`:** untracked and ignored; the operator moved it to `..\env.harness.keep`. It is still in
  git history (since `fa5b1eb`). **Rotation of the key is unconfirmed.**
- My device shell shows CRLF-only "modified" noise on some files. Windows git is clean. Check with
  `git diff --ignore-cr-at-eol --stat`.

## 7. Next steps (detail in `step3-scope-cut-plan.md`)

1. Run ultrareview slices 2 and 3 (commands in the plan, §F) and triage them like slice 1.
2. Resolve wayfinder W03 (most important), W01 and W02: AFK research, one session each, in parallel.
3. Grill W04, then W05 (and W06 only if W05 implies harness support).
4. Operator Step 0: rotate the key, write `BASELINE.md` (Windows `py -3.10 -m pytest -q`), `git worktree prune`.
5. Thu 5: the scope-cut grill over the merged list. The recommended keeps are UR-A, UR-B, UR-C, 01 (+ the
   finding-5 box), 03 if Converse, plus 1–3 wayfinder must-lands. Defer 02, 04–06 and 07a–09.
6. `to-tickets` for the keeps (`issues/10-…`), set `ready-for-agent`, comment on the deferrals, write
   `discovery/scope-cut-2026-11-05.md`, and update plan §4/§6.
