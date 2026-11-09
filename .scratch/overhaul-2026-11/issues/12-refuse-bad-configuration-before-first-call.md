# 12 — Refuse a bad configuration before the first assessor call (UR-A)

Status: ready-for-agent
Type: task
Blocked by: 10
Source: `discovery/ultrareview-run-path-2026-11-04.md` findings 2, 3, 4; `../overhaul-2026-11-f7-wayfinder/W03-findings.md` §3
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · DN run path (V14/V16 on Converse)

## What to build

A blind assessment that cannot finish refuses before it spends anything, with the fail-closed exit code 2
and a message naming the problem. Today four configurations pass the up-front checks and fail later:

- the preflight records a rubric whose declared anchor is missing from the candidate as a "not built" pack
  and accepts it; `assess` then crashes mid-run when building that pack (finding 2);
- `--criterion-n` below the majority minimum is rejected only after every cell call, and the checkpoint
  binding then blocks resuming with a corrected value (finding 3);
- a Converse misconfiguration (no region in production mode, no model, backend not allowed in production)
  raises a plain error that ends in a traceback instead of exit 2 (finding 4);
- an omitted `--transport` on the host defaults to `openai-compatible` and ends in a raw `base_url` error
  (W03 §3).

## Decisions (scope cut, 2026-11-06)

- All four become refusals **before the first assessor call**, in the command's existing pre-flight checks.
- The omitted-transport case refuses by naming the route the environment resolves to and the flag to
  pass. No route is inferred. This replaces deferred ticket 03 for the DN path.
- Finding 1 (criterion budget on `openai-compatible`) is **out**: off route under Converse.
- No change to report or checkpoint formats.

## Acceptance criteria

Failing tests first:

- [ ] A preflight over a candidate missing a declared rubric anchor fails the preflight (or `check_preflight`), naming the anchor.
- [ ] `--criterion-n` below the minimum is refused before any call (fake backend records zero calls).
- [ ] Each Converse misconfiguration exits 2 with a one-line reason, no traceback.
- [ ] No `--transport` with an environment resolving to `bedrock_converse`: exit 2 naming `--transport bedrock-converse`.
- [ ] A valid Converse configuration on the fake backend runs exactly as today.

Then:
- [ ] **PE-09 acceptance lane green**, run with ticket 10's lane (admission rule 5).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/12-refuse-bad-configuration-before-first-call.md   Base commit: <sha after 10 merged>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md,
            .scratch/overhaul-2026-11/discovery/ultrareview-run-path-2026-11-04.md
Seam: the assess/preflight command's up-front checks — no interface change
Do not touch: judge internals (ticket 01, deferred), response_cache binding (ticket 15),
      runner/transport/*, report/checkpoint schemas, freeze conditions, Tier 1–3 docs
Skills: diagnosing-bugs (reproduce each as a failing test), then tdd
Size: ~120–200 changed non-test lines
Record: none
```

## Out of scope

- Finding 1; judge-factory unification (ticket 03, deferred).
