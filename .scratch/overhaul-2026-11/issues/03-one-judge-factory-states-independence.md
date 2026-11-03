# 03 — One place that builds a judge and states its independence

Status: needs-triage
Type: task
Blocked by: 01
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate B. Not grilled; the
operator asked for the ticket directly on 2026-11-03, and every recommendation below was taken as the
decision.
Findings: F5 · DN critical path (assessor construction) · one confirmed misroute defect

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.
> Blocked by 01 because both change the judge module and the blind-assessment command. It touches only
> the judge-building lines of rubric grading, so it does not need to wait for 02.

## What to build

Every harness command gets its judge from one place, and that place states, per route, which kinds of
independence hold. Today a judge is built six ways:

- the lazy default inside the judge (used by materiality calibration and the rubric-grid helper);
- the paced OpenAI-compatible builder (grounding freeze, rubric grading, the blind-assessment default);
- a second copy of it in faithfulness calibration;
- the Converse builder;
- the subscription builder.

Grader–generator independence is enforced with different logic on different routes, and a backend
passed in directly skips the transport check entirely.

There is also a live defect. Both paced builders refuse `claude_cli` and then always build an
OpenAI-compatible backend. If the environment resolves to Bedrock Converse, rubric grading, grounding
freeze and faithfulness calibration speak the wrong backend instead of refusing.

After this ticket, a command names a route, the factory checks that the environment agrees, applies
that route's independence policy, and returns the judge with its retry wrapper.

## Decisions (operator accepted recommendations, 2026-11-03)

- **One factory, in `harness/`, outside `commands/`.** It owns route selection, the per-route
  independence policy, pacing / retry wrapping and provenance-log wiring. It stays on the harness side
  of the one-way import rule; `runner/transport` is not changed.
- **Three routes.** Each keeps today's name, as recorded in `assessor_transport`:
  - `openai-compatible`: paced and retrying;
  - `bedrock-converse`: retrying, not paced;
  - `claude-cli`: the subscription assessor.
- **The route is explicit and the environment must agree.** A mismatch is refused, naming both. This
  is the fix for the misroute defect; no route is ever inferred silently.
- **Independence policy as one table**, read by the factory and by `HARNESS.md`:
  - the model guard (`JudgeConfig`, drafter models refused) applies on every route, unchanged;
  - `openai-compatible` / `bedrock-converse` refuse a `claude_cli` environment;
  - `claude-cli` requires a Claude pin, an empty tool list (no tools, strict MCP config), and a fresh
    working directory outside the repository;
  - the rule that the version tag must name the transport stays exactly where it applies today
    (`bedrock-converse`, `claude-cli`). It is not extended to `openai-compatible`, so existing pins
    and reports stay valid.
- **No lazy default.** The judge no longer builds a backend on its own; it must be given one. The two
  production callers that relied on the lazy default move to the factory.
- **No new CLI surface.** Commands keep their current choices: blind assessment keeps `--transport`,
  and the other commands use `openai-compatible` as today. Adding route flags elsewhere is out of scope.

## Acceptance criteria

Failing tests first:

- [ ] The environment resolves to `bedrock_converse` and the `openai-compatible` route is asked for: it is refused, naming both. (Today an OpenAI-compatible backend is built.)
- [ ] The same mismatch check holds for every route pair.
- [ ] A drafter model is refused on every route.
- [ ] A judge constructed without a backend raises; there is no lazy default build.
- [ ] A boundary test: no harness module other than the factory constructs a judge with a production backend.

Characterisation, pinned before anything moves:

- [ ] The `claude-cli` route still refuses a non-Claude pin, a version without the transport tag, and a working directory inside the repository, and still passes the empty tool list.
- [ ] The `bedrock-converse` route still requires its version tag and applies retry without pacing.
- [ ] The `openai-compatible` route applies the same pacing and retry parameters as before.
- [ ] Blind reports record the same `assessor_transport` strings as before.

Then:

- [ ] Faithfulness calibration's private builder and the paced builder in grounding freeze are gone; every command calls the factory.
- [ ] `harness/HARNESS.md`'s guardrail table points at the factory's policy table, and the subscription module's "what independence survives" account stays accurate.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5: blind-assessment command and assessor construction change).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/03-one-judge-factory-states-independence.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, issue 01 (landed), harness/commands/_subscription_judge.py docstring
Seam: judge construction — before: six construction routes plus the judge's lazy default;
      after: one factory (route, pin, pacing) → judge + wrapper; the judge requires an injected backend
Do not touch: runner/transport/*, the JudgeConfig model guard, the blind-assessment binding or report
      schema (beyond keeping assessor_transport strings), §17 call graph, Tier 1–3 docs
Tests first: the five failing tests above, then the four characterisation tests (tdd)
Size: ~250–350 changed non-test lines
Record: no decision-log entry needed
```

## Out of scope

- Moving transport adapters across the harness/runner seam (runtime candidate A is the runner-side counterpart).
- New `--transport` flags for commands that don't have one.
- Making the two JSON-extraction rules consistent.
