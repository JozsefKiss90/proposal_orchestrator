# Wayfinder map — F7: a trustworthy V16 run on the 2026 DN candidate

Label: wayfinder:map
Charted: 2026-11-04 (operator + Claude) · base HEAD `5ba39e2d` (branch `harness_overhaul`)
Feeds: overhaul Step 3 scope cut (`plans/overhaul_2026-11_plan.md` §2, §4 item 5)

## Destination

A **decided list of harness changes that must land by the 10 Nov code freeze**, so that the V16 Stage B
blind assessment of the 2026 DN candidate, run before the 23 Nov deadline, comes out **frozen, audited,
advisory, and explicit about what it did not assess**. Each item on the list is either an existing overhaul
ticket (01–09), a new ticket for Step 3, or an operator step with a date. The map is done when nothing is
left to decide before the scope cut and the operator sessions.

## Notes

- **Domain.** MSCA-DN pre-evaluation, branch `msca-dn-pre-eval`. Ledger:
  `plans/msca_dn_historical_validation_tickets.md` (V01–V18, X01–X04). Anonymisation:
  `.scratch/msca-dn-anonymisation/tickets.md` (AN0–AN15). Runbook: `plans/msca_dn_pe09_runbook.md` (§7 is
  stage A → B). Glossaries: `harness/CONTEXT.md`, `runner/CONTEXT.md`.
- **Skills every session should consult:** `grilling` and `domain-modeling` for HITL tickets; `research`
  for AFK tickets (findings saved as a Markdown file in this folder, then linked).
- **Planning only.** No code, no ledger edits, no `CLAUDE.md` edits. Decisions only, recorded per ticket.
- **Tracker.** Local Markdown (`docs/agents/issue-tracker.md`, "Wayfinding operations"). Children are
  `issues/NN-<slug>.md`, numbered in this folder. `Status: open | claimed | resolved`. `Blocked by:` lines.
- **Trust the code, not the checkboxes.** Ledger checkboxes have drifted (F1). Check commits and
  `plans/reports/` before treating an item as open.
- **Never print `.env.harness`**, and no private proposal content in the repo (AN constraint, V17/V18 pattern).
- **Operator decisions taken when the map was charted (2026-11-04):**
  1. Destination: as above.
  2. **V14 before V16, V15 not required.** Stage A (V14) runs first, so the 2026 score can be read against
     a measured original-vs-ESR gap. The ledger's "V16 blocked by V15" edge is to be relaxed to "blocked by
     V14". The ledger edit itself is a later operator action and is not made by this map.
  3. **Venue.** V16 runs on the private host, with the same Converse model and sample plan as V14. No
     anonymisation of the 2026 candidate.
  4. **Grounding scope.** V16 declares grounding **unassessable**. X01 is off the route.
  5. **Scope.** See "Out of scope". The AN chain (AN12a–AN15) and V02c stay **in** scope.

## Decisions so far

<!-- one line per resolved ticket: [title](issues/NN-slug.md) — gist -->
- [04 — Does AN15 ride in the V14 session?](issues/04-does-an15-ride-in-the-v14-session.md) — skipped by the operator (2026-11-06): AN15 does not ride; AN12a not must-land; AN chain deferred past 23 Nov.
- [03 — V14/V16 run path and on-route tickets](issues/03-v14-v16-run-path-and-on-route-tickets.md) — transport is an operator call (host not built; runbook says claude-cli); 03's misroute is off route; only 01 changes assessment output; lane RED at HEAD (stale declaration drafts); V02c done.
- [01 — Import route for the 2026 candidate](issues/01-import-route-for-the-2026-candidate.md) — not with today's code: the importer's document set is closed; must-land W-1 declares a fourth submitted-document config (~60–80 lines); every other step is config only.
- [02 — Profile applicability for stage B](issues/02-profile-applicability-for-stage-b.md) — sourced via the V09 index (all 2026 hashes match) and the derived scorecard, not in the profile file; confirm with one operator applicability record (call binding, form v2.2 Inferred); no code. WP deadline is 24 Nov 2026.
- [05 — V14 timing and locked revision](issues/05-v14-timing-and-code-revision-lock.md) — Converse on the host; one bundle from the 10 Nov freeze commit for V14 and V16, nothing lands between; AN12 criteria 1 + 3 only; 10 Nov bundle → 11 R11 → 12 AN12 → 13–15 V14 → ~19–20 V16 → 24 Nov.
- [06 — How V16 may read V14's gap](issues/06-how-v16-may-read-v14s-gap.md) — prose caveat in the operator's review only; no harness support.

## The must-land list (assembled 2026-11-06; the map's destination)

All six map tickets are resolved. What must be true for a frozen, audited, advisory V16 that states what it
did not assess:

**Code, in the 10 Nov freeze-commit bundle (Step 3 candidates; the cut decides which of the optional ones fit):**

| Item | Source | Status for the cut |
|------|--------|--------------------|
| W-1 — declare the 2026 resubmission as its own document in the importer (~60–80 lines) | W01 | **must land**: without it V16 cannot import its candidate |
| UR-A, UR-B, UR-C — refusals before the first paid call, resume binding covers the inference configuration, receipt guard anchored on this repository | ultrareview slice 1 | on path, no output change; recommended keeps |
| UR-E — the integrity audit never loses or overwrites a DC project | ultrareview slice 2 | on path (audit); recommended keep |
| UR-D — the acceptance lane is GREEN only when the run proved it | ultrareview slice 2 | the rule-5 gate itself; recommended keep |
| Ticket 01 — deepen the judge call | harness review | on path and **the only output-changing item**: by 10 Nov or after V16 (W05 Q1) |
| Slice-2 findings 1 and 2 (profile CLI sixth check; provenance fallback) | ultrareview slice 2 | small; optional |

Off route: ticket 03 (its misroute does not reach the blind assessment), 02, 04–06 (no output value before the
runs), 07a–09 (runner side).

**Before any rule-5 ticket:** re-render the declaration drafts (`py -3.10 -m tools.draft_fidelity_declarations`,
then `--check`); the PE-09 acceptance lane is RED at HEAD until then (W03 §5.1).

**Docs and records (may follow the lock; they change no bundled behaviour):** the PE-09 runbook's Converse
delta (V14/V16 command lines, version-tag rule, receipt section, the stage-B `--document` id); the Stage B
profile-applicability decision record (W02); the ledger edit relaxing V16's blocker from V15 to V14 (§9.4).

**Operator schedule:** see ticket 05 (Q3).

## Not yet specified

- **The V16 operator runbook delta**, now scoped above (Converse lines + stage-B document id); its text is
  still to be written.
- **V16 criterion 1** (human-approved changes land in authoritative inputs, each with its human
  confirmation). Is any of it harness-checkable, or is it purely a drafting-process attestation?
- **The ledger edit** relaxing V16's blocker to V14: when, and in which successor record (§9.4).
- **Repeatability vs time budget.** AN15 no longer rides (W04). Whether V14's sample plan fits Fri 13–Sun 15
  is measured on the host by AN12 criterion 3's synthetic Converse pass (Thu 12).

## Out of scope

- PF evaluation-harness lane: E5f, E5.1, E6–E9, the `harness/calibration.py` None-guard, the E1.5 gold-set
  mislabels. The DN blind assessment doesn't use them. (Operator, 2026-11-04.)
- X02 (DN graph entities), X03 (human DN calibration data), X04 (cross-baseline comparison tool). None
  blocks V14 or V16. (Operator, 2026-11-04.)
- X01 (imported-source grounding). Ruled off the route by decision 4; it returns only if a source-grounded
  scope is wanted after 23 Nov.
