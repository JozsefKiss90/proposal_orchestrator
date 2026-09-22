# Proposal Orchestration — Project Vocabulary

Ubiquitous language for the proposal currently instantiated in Tier 3. Constitutional
meanings live in `CLAUDE.md`; this file only pins vocabulary. The runtime module map is
`plans/reports/CONTEXT.md`.

No project is instantiated. Tier 3 is empty. Populate this file when you seed a project:
add one entry per term the team uses that a newcomer could misread, in the form below.

## Language

**Submission master**:
The page-limited, manually condensed Part B document that is actually uploaded to the
portal. Exactly one exists per submission window; it is frozen (hash recorded) before upload.
_Avoid_: final draft, condensed draft

**Regeneration run**:
A pipeline run (Phases 1–8) executed *before* submission so the submitted text derives
from updated Tier 3 state.
_Avoid_: reconciliation run (that is a post-submission comparison run), reinstatement

**Surgical Tier 3 update**:
A minimal, decision-traceable set of edits to named Tier 3 artifacts that leaves every
phase gate passable. Nothing is restored from history.
_Avoid_: reinstatement, restore

**Supervision spine**:
The named seat assignments SUPERVISOR / CO_SUPERVISOR / HOST / associated-partner
representatives, as tokenised in `call_binding/confirmation_checklist.json`. Each seat
carries its own Confirmed / Inferred / Assumed / Unresolved status.
_Avoid_: identity spine (older records), supervision arrangement

**Fallback (open decision)**:
The pre-stated honest position an open decision takes automatically at its cut-off. A
fallback never strengthens a claim.

<!-- Project-specific terms (sites, partners, milestones, domain objects) go below this
     line once Tier 3 is populated. Use the same **Term**: / _Avoid_: shape. -->
