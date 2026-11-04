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

## Not yet specified

- **The must-land list itself.** It assembles once tickets 01–06 resolve. It may graduate into Step 3
  candidate tickets (new harness fixes) rather than map tickets.
- **The V16 operator runbook delta.** What changes in the PE-09 runbook for a Stage B candidate beyond §7:
  revision entry, register, profile flag, receipt. Depends on 01 and 02.
- **V16 criterion 1** (human-approved changes land in authoritative inputs, each with its human
  confirmation). Is any of it harness-checkable, or is it purely a drafting-process attestation?
- **The ledger edit** relaxing V16's blocker to V14: when, and in which successor record (§9.4).
- **Repeatability vs time budget.** Whether V14's sample plan fits the operator's time before 23 Nov
  twice over (V14 + V16, plus AN15 if it rides along).

## Out of scope

- PF evaluation-harness lane: E5f, E5.1, E6–E9, the `harness/calibration.py` None-guard, the E1.5 gold-set
  mislabels. The DN blind assessment doesn't use them. (Operator, 2026-11-04.)
- X02 (DN graph entities), X03 (human DN calibration data), X04 (cross-baseline comparison tool). None
  blocks V14 or V16. (Operator, 2026-11-04.)
- X01 (imported-source grounding). Ruled off the route by decision 4; it returns only if a source-grounded
  scope is wanted after 23 Nov.
