# 13 — Anchor the receipt guard on this repository (UR-C)

Status: ready-for-agent
Type: task
Blocked by: 10
Source: `discovery/ultrareview-run-path-2026-11-04.md` finding 7
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · private-content guard (V13 receipt, V14/V16)

## What to build

The readiness-receipt validator refuses a receipt stored inside this repository wherever it is run from.
Today the guard checks the receipt path against `--repo-root` (default `.`), not against the repository
itself, so running from elsewhere, or with `--repo-root` pointed at the profile's directory, accepts an
in-repo receipt that holds private paths. `converse_smoke.check_receipt` already anchors on the repository
correctly; this command does the same.

## Acceptance criteria

Failing tests first:

- [x] A receipt inside the repository is refused when the command runs with a different working directory.
- [x] Same with `--repo-root` pointed at a subdirectory (e.g. the profiles directory).
- [x] A receipt outside the repository is accepted exactly as today.

Then:
- [ ] **PE-09 acceptance lane green**, run with ticket 10's lane (admission rule 5).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [x] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/13-receipt-guard-anchored-on-this-repository.md   Base commit: <sha after 10 merged>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md
Seam: the receipt command's path guard — no interface change
Do not touch: receipt schema, transport tables, other commands, Tier 1–3 docs
Skills: diagnosing-bugs, then tdd
Size: ~10–30 changed non-test lines
Record: none
```
