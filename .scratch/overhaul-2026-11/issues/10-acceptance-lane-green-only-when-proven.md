# 10 — The acceptance lane is GREEN only when this run proved it (UR-D)

Status: ready-for-agent
Type: task
Blocked by: None — can start immediately (after the declaration-drafts re-render, an operator step)
Source: `discovery/ultrareview-records-2026-11-06.md`, findings 3, 4, 8 (7 if cheap)
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · the rule-5 gate itself

## What to build

The PE-09 acceptance lane reports GREEN only when the run it reports on actually executed every lane
module and proved the result. Today a GREEN can be produced without that:

- with `--junit PATH`, a report left at PATH by an earlier run is read when pytest writes no new one, and
  pytest's own exit code is ignored (finding 3);
- reconciliation never checks that the report covers the lane's modules or that skips match
  `declared_skips`, so a narrowed run reconciles GREEN and certified (finding 4);
- a narrowed run (`--area`, `-k`) exits 0 like a GREEN one, although the docstring says a narrowed run is
  never an acceptance result (finding 8);
- `--from-junit` takes certification from the machine re-reading the report, not the build that produced
  it (finding 7).

Every rule-5 ticket in this cut (12–16) cites "lane green", so this lands first.

## Decisions (scope cut, 2026-11-06)

- **Fresh evidence only.** A report path that already exists before the run is refused, and a run where
  pytest did not write a new report, or exited non-zero for a reason other than test failures, is not GREEN.
- **Coverage is checked.** GREEN needs every lane module present in the report, and skips that are exactly
  the declared ones; a missing module or an undeclared skip is a finding, never GREEN.
- **Narrowed is never acceptance.** A narrowed run exits non-zero (or with a distinct code) and says
  "not an acceptance result".
- **Finding 7** (certification on `--from-junit`) is in only if it fits; otherwise `--from-junit` output
  says it is not certified, and the finding is recorded as deferred.
- The lane definition file and its exclusions are unchanged.

## Acceptance criteria

Failing tests first (they exercise the lane module and command directly, not through the lane):

- [ ] A stale report at the `--junit` path with pytest writing nothing: not GREEN, names the stale file.
- [ ] Pytest exits with a collection/usage error: not GREEN, regardless of the report.
- [ ] A report missing one lane module: not GREEN, names the module.
- [ ] A skip not in `declared_skips`: not GREEN (characterise first; it may already hold).
- [ ] `--area` or `-k`: exit code is not 0, output says "not an acceptance result".
- [ ] A full, fresh, passing run on fixtures: GREEN and certified exactly as today.

Then:

- [ ] `harness/ACCEPTANCE_LANE.md` states the four conditions.
- [ ] One real lane run at the end of the session on HEAD: GREEN (requires the drafts re-render).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/10-acceptance-lane-green-only-when-proven.md   Base commit: <sha of the scope-cut commit>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md, harness/ACCEPTANCE_LANE.md
Seam: the acceptance-lane reconciliation — interface unchanged; stricter GREEN
Do not touch: harness/acceptance_lanes/*.json (lane definition, exclusions), other harness modules,
      §17 call graph, Tier 1–3 docs
Skills: diagnosing-bugs (reproduce findings 3/4/8 as failing tests), then tdd
Tests first: the six above, in order
Size: ~100–180 changed non-test lines
Record: no decision-log entry (out-of-band harness); note the stricter rule in ACCEPTANCE_LANE.md
```

## Out of scope

- Changing the lane's module set, exclusions or declared skips.
- Duplicate `one_line` helper (finding 9).
