# FIELDWISE Proposal Orchestration

Ubiquitous language for the FIELDWISE MSCA-PF proposal work (Tier 3 substrate, runs, and
submission artifacts). Constitutional meanings live in `CLAUDE.md`; this file only pins
vocabulary. The runtime module map is `plans/reports/CONTEXT.md`.

## Language

**Submission master**:
The page-limited, manually condensed Part B docx that is actually uploaded to the portal.
Exactly one exists per submission window; it is frozen (hash recorded) before upload.
_Avoid_: final draft, condensed draft

**Regeneration run**:
A pipeline run (Phases 1–8) executed *before* submission so the submitted text derives
from updated Tier 3 state. `fieldwise-run-03` is a regeneration run.
_Avoid_: reconciliation run (that is a post-submission comparison run), reinstatement

**Surgical Tier 3 update**:
A minimal, decision-traceable set of edits to named Tier 3 artifacts that leaves every
phase gate passable. Nothing is restored from history — Tier 3 was never deleted.
_Avoid_: reinstatement, restore

**Supervision spine**:
The named seat assignments SUPERVISOR / CO_SUPERVISOR / HOST / associated-partner
representatives, as tokenised in `call_binding/confirmation_checklist.json`. Since
2026-09-02: SUPERVISOR Dr. Tibor Janda (HUN-REN ATK), CO_SUPERVISOR Prof. András Jung
(ELTE), Dr. Roland Hollós ELTE-side named ML team member — all Assumed.
_Avoid_: identity spine (older records), supervision arrangement

**Farmer 2**:
The identified second commercial processing-tomato producer serving as first-line site
backup. Activation preserves the commercial-transferability claim. Not the Skanzen
contingency.
_Avoid_: backup farmer, second site

**Skanzen contingency**:
The Szentendre model-garden fallback, last tier of the site ladder. Activation preserves
the measurement programme only; the commercial-transferability claim is downgraded and
reported as such.
_Avoid_: backup site (ambiguous with Farmer 2)

**Site ladder**:
The ordered contingency chain for the WP-validation field site: primary farmer →
Farmer 2 → Skanzen.

**MVCRI**:
Maritsa Vegetable Crops Research Institute (Plovdiv, BG), the fellow's employer and the
post-MSCA transfer route for cultivar-level validation. On no WP line; no in-action
effort.
_Avoid_: MCVI, MVCRI trial seat

**Model freeze**:
The M3 milestone at which the primary model's parameters are fixed and its model card
registered, before the first prospective field season. Post-freeze modelling work is
scale-harmonisation and crop-transfer specification, never target-model changes.

**Fallback (open decision)**:
The pre-stated honest position an open decision takes automatically at its cut-off. A
fallback never strengthens a claim.
