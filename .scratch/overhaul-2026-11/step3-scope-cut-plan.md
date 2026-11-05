# Step 3 — scope cut: what is left to close it

Written 2026-11-04 (Wed). Plan: `plans/overhaul_2026-11_plan.md` §2 (Step 3 on Thu 5), §3 admission rules.
**Step 3 is closed when:** one merged candidate list has been grilled down to **5–8 tickets** that each pass
§3; those are `ready-for-agent` with session briefs in dependency order; every other candidate carries a
recorded disposition. This file names what is still missing and in what order.

## A. State at the time of writing

| Input to the cut | State |
|------------------|-------|
| Harness architecture pass | done → tickets 01–06 (`needs-triage`) |
| Runtime architecture pass | done → tickets 07a, 07b, 08, 09 (`needs-triage`); E not taken (`discovery/decision-E-tapm-banner-2026-11-04.md`) |
| Ultrareview | slice 1 done, 10 findings (`discovery/ultrareview-run-path-2026-11-04.md`); **slices 2 and 3 not run** |
| Wayfinder F7 | map charted (`../overhaul-2026-11-f7-wayfinder/map.md`); **tickets W01–W06 open, none resolved** |
| Step 0 | `.env.harness` untracked (`83c210e9`, `09baceac`). **Key rotation unconfirmed.** **`plans/overhaul/BASELINE.md` missing.** **3 prunable worktrees.** |
| Step 1 (F1 checkboxes, F2 `AGENTS.md` drift) | **not started** |

## B. Before the grill (Wed 4 evening → Thu 5 morning)

In this order. The first three run in parallel.

1. **Ultrareview slices 2 and 3** (free runs 2 and 3, about 20 min each, operator in Claude Code; commands in §F).
   Triage each finding the same way as slice 1: on path? covered? disposition.
2. **Wayfinder W03, run path and on-route tickets** (research, AFK, one Claude Code session). This is the
   most important input. It decides which of 01–09 and UR-A/B/C touch the code V14/V16 execute, settles
   V14's transport (the runbook says `claude-cli`, the map says Converse), and reports V02c and acceptance
   lane status.
3. **Wayfinder W01 (import route) and W02 (profile applicability)** (research, AFK, one session each).
   Either may add a must-land code item for V16.
4. **Wayfinder W04, does AN15 ride in V14?** (grilling, ~10 min with Claude). If yes, AN12a (code) is a
   must-land candidate.
5. **Wayfinder W05, V14 timing and locked revision** (grilling, after W03 and W04). This sets the rule
   for what may land between V14 and V16, which is the cut's hard boundary.
6. **Wayfinder W06** (how V16 reads V14's gap). It can wait until after the cut **unless** W05's answer
   implies harness support (a report field or a linking record). Then grill it before the cut.
7. **Step 0, the operator's part:**
   - confirm the key is rotated;
   - run `py -3.10 -m pytest -q` on Windows and write `plans/overhaul/BASELINE.md` (pass, fail, skip,
     wall time);
   - `git worktree prune`.

   The baseline doesn't block the cut, but it blocks every Step 4 session, because each "done when" cites it.

Each wayfinder ticket resolves in its own session, appends its answer, sets `Status: resolved`, and adds
one line to the map's Decisions-so-far.

## C. The merged candidate list (input to the grill)

Recommendation in the last column. Final decisions are the operator's at the grill.

| ID | Candidate | Source | On V14/V16 path | §3 notes | Recommendation |
|----|-----------|--------|-----------------|----------|----------------|
| UR-A | Refuse bad configuration before the first assessor call (findings 2, 3, 4, opt. 1) | ultrareview 1 | yes | small; rule 5 | **keep** |
| UR-B | Resume binding covers the inference configuration (finding 6) | ultrareview 1 | yes | small; rule 5 | **keep** |
| UR-C | Receipt guard anchored on this repository (finding 7) | ultrareview 1 | yes | tiny; rule 5 | **keep** (could merge into UR-A only if one seam; it isn't) |
| 01 | Deepen the judge call (+ finding 5 box, + finding 8 note) | harness | yes (judge on every draw) | ~300 lines; rule 5 | **keep** |
| 03 | One judge factory, states independence (live Converse defect) | harness | yes if V14/V16 use Converse (W03) | blocked by 01 | **keep if W03 confirms Converse** |
| W-x | Must-land items from W01/W02/W04/W05 (e.g. import-route fix, profile sourcing, AN12a) | wayfinder | yes by construction | unknown size | **keep, up to 2–3 slots** |
| UR-2/3 | New tickets from slices 2/3 | ultrareview | slice 2 yes; slice 3 V14 only | — | rank alongside UR-A–C |
| 04 | One content-hash module (covers finding 9) | harness | touches preflight/baseline | groundwork for 05/06 | defer past 23 Nov |
| 02 | Rubric grading resumes from the response checkpoint | harness | **no** (rubric lane) | blocked by 01 | defer |
| 05, 06 | DN record chain expand/contract | harness | yes (records), but refactor | blocked by 04 | defer |
| 07a, 07b, 08, 09 | Runtime extractions | runtime | no DN value before 23 Nov | 09 needs PE-09 | defer (plan §4 item 6: only if testability blocks) |
| F2 | `AGENTS.md` generated from `CLAUDE.md` + drift test | Step 1 | no | hygiene | optional slot if under 8 |
| F1 | Reconcile ticket checkboxes with `git log` | Step 1 | no | operator approval | do outside the ticket budget, or defer |
| — | Calibration None-guard, E-lane, X01–X04, finding 10 | various | no | — | out (wayfinder "Out of scope"; hygiene) |

Likely shape: **UR-A, UR-B, UR-C, 01 (+03)** plus **1–3 wayfinder must-lands** plus any critical
slice 2/3 finding. That is 5–8, and almost entirely on the DN path.

## D. The grill (Thu 5, ~30 min, `grilling`)

One question at a time, each with a recommendation:

1. Is the hard boundary from W05 accepted (what may land before V14 / between V14 and V16)?
2. For each "keep": does it pass all five §3 rules? Watch rule 3 (size) for 01 and any W-x item.
3. Is 03 in? It depends on W03's transport answer.
4. Which slice 2/3 findings displace a lower-ranked keep?
5. Is anything in "defer" really on the critical path? The burden of proof is on keeping it.
6. Execution order and blocking edges for Thu 5 → Sun 8 (01 before 03; UR-A/B/C independent).

## E. After the grill: closing Step 3

1. `to-tickets`: write UR-A, UR-B, UR-C (and any W-x / UR-2/3 keeps) as `issues/10-…` onward, in the 01–09
   format: decisions, failing tests first, acceptance incl. PE-09 lane, session brief with
   `Base commit: <sha at start>`.
2. Amend ticket 01: add the finding 5 box and the finding 8 note.
3. Set kept tickets to `Status: ready-for-agent`. For deferred ones, keep `needs-triage` and append
   `## Comments` → "Deferred at Step 3 (2026-11-05): <reason>". Use `wontfix` only for a real "no".
4. Record the cut: a short `discovery/scope-cut-2026-11-05.md` (kept list, order, deferrals and why), and
   update plan §4/§6. Ultrareview scope is decided; the TAPM banner decision is E.
5. Step 4 can start once `BASELINE.md` exists.

## E2. Where `code-review` and `diagnosing-bugs` run (plan §1 "Review"/"Fix" rows)

Both are **Step 4** skills, used inside each ticket's implementation session, not in Step 3.

- **`code-review`**: once per ticket, at the end of its session, over the diff since the ticket's base
  commit. Standards axis = `CLAUDE.md` §16–17; spec axis = the ticket text. It is already an acceptance box
  and a session-brief line in every ticket; the new UR tickets must carry it too.
- **`diagnosing-bugs`**: first step of every ticket that fixes a confirmed defect. Reproduce it as a
  failing test, then fix it. The plan's three defect types land as follows:

| Defect | Ticket | Note |
|--------|--------|------|
| Ultrareview-confirmed (slice 1 findings 2, 3, 4, 6, 7; finding 5) | UR-A, UR-B, UR-C; ticket 01 | Name `diagnosing-bugs` in each UR session brief, before `tdd`. Same for any slice 2/3 keeps. |
| F6 checkpoint fingerprint (rubric resume misses a replaced section) | ticket 02 | Recommended defer: rubric lane, not the DN path. The DN blind-assessment resume gap is finding 6, in UR-B. |
| Groq malformed JSON | ticket 01 (redraw, fail closed); ticket 03 (`response_format`) | Groq is not the V14/V16 transport, so this is lower DN risk than the plan assumed. |

Optional before the grill: a quick local reproduction of finding 2 or 6, only if you want to see a defect
fail before giving it a slot. Ultrareview already verified each finding.

## F. Ultrareview slices 2 and 3: commands (PowerShell, from a clean tree)

All slice files are new since `main`, so the base only removes them. Each PR's base must be the `ur/base-…`
branch, never `main`. Check "Files changed" before running.

Slice 2, records (9 files, about 5,960 lines):

```powershell
git switch -c ur/base-records msca-dn-pre-eval
git rm -q harness/integrity_audit.py harness/candidate_provenance.py harness/grounding_scope.py harness/profile.py harness/historical_profile.py harness/commands/historical_profile.py harness/acceptance_lane.py harness/commands/acceptance_lane.py harness/criterion_scoring.py
git commit -m "ultrareview base: records slice removed"
git push -u origin ur/base-records
git switch -c ur/review-records
git revert --no-edit HEAD
git push -u origin ur/review-records
gh pr create --draft --base ur/base-records --head ur/review-records --title "ultrareview: records slice (review only, do not merge)" --body "Review-only PR. Close without merging."
claude ultrareview <PR#> --timeout 60 | tee ~/ultrareview-records.txt
git switch harness_overhaul
```

Slice 3, ESR side (7 files, about 6,920 lines):

```powershell
git switch -c ur/base-esr msca-dn-pre-eval
git rm -q harness/esr_comparison.py harness/operator_review.py harness/comparison_diff.py harness/deferral_register.py harness/commands/deferral_register.py harness/authority_matrix.py harness/commands/authority_matrix.py
git commit -m "ultrareview base: ESR slice removed"
git push -u origin ur/base-esr
git switch -c ur/review-esr
git revert --no-edit HEAD
git push -u origin ur/review-esr
gh pr create --draft --base ur/base-esr --head ur/review-esr --title "ultrareview: ESR slice (review only, do not merge)" --body "Review-only PR. Close without merging."
claude ultrareview <PR#> --timeout 60 | tee ~/ultrareview-esr.txt
git switch harness_overhaul
```

Without `gh`, open `https://github.com/JozsefKiss90/proposal_orchestrator/compare/ur/base-records...ur/review-records`
(or `…/ur/base-esr...ur/review-esr`) and create a draft PR there. Expected "Files changed": slice 2 is 9 files
+5,958 −0, slice 3 is 7 files +6,919 −0.
