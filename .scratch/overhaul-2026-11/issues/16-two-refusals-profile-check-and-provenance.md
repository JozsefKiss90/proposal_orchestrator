# 16 — Two refusals: the profile check runs in full, provenance never borrows a revision (UR-F)

Status: ready-for-agent
Type: task
Blocked by: 10
Source: `discovery/ultrareview-records-2026-11-06.md` findings 1, 2
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · V14 profile check; V16 provenance

## What to build

Two checks that should refuse, refuse:

- the historical-profile command calls the profile check without the matrix status, so the documented
  sixth check (a status the matrix cannot carry) never runs from the command that the runbook tells the
  operator to run before V14 (finding 1);
- the import-manifest lookup falls back to a `document_id` match even when the caller named a `node_id`
  that matched nothing, so it can return another revision's manifest (finding 2). A named node that is not
  found is "not found".

## Acceptance criteria

Failing tests first:

- [ ] The command runs all six checks; a profile with a status the matrix cannot carry fails from the command.
- [ ] A lookup with a `node_id` that matches nothing returns not-found even when exactly one manifest has the `document_id`.
- [ ] A lookup with only a `document_id` and one manifest still resolves it, as today.

Then:
- [ ] **PE-09 acceptance lane green**, run with ticket 10's lane (admission rule 5).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/16-two-refusals-profile-check-and-provenance.md   Base commit: <sha after 10 merged>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md,
            .scratch/overhaul-2026-11/discovery/ultrareview-records-2026-11-06.md
Seam: none (two internal fixes, no interface change)
Do not touch: the integrity audit parser (ticket 14), the profile files, the matrix, Tier 1–3 docs
Skills: diagnosing-bugs, then tdd
Size: ~10–40 changed non-test lines
Record: none
```

## Out of scope

- Unused imports (finding 10).
