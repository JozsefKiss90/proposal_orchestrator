# 03 — One place that builds a judge and states its independence

Status: in-progress
Type: task
Blocked by: 01
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate B. Not grilled; the
operator asked for the ticket directly on 2026-11-03, and every recommendation below was taken as the
decision.
Findings: F5 · DN critical path (assessor construction) · one confirmed misroute defect

> Admitted by operator decision D2 (`docs/tier4_orchestration_state/decision_log/plan-order-reliability_2026-11-11.json`); 01 has landed.

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

- [x] The environment resolves to `bedrock_converse` and the `openai-compatible` route is asked for: it is refused, naming both. (Today an OpenAI-compatible backend is built.)
- [x] The same mismatch check holds for every route pair.
- [x] A drafter model is refused on every route.
- [x] A judge constructed without a backend raises; there is no lazy default build.
- [x] A boundary test: no harness module other than the factory constructs a judge with a production backend.

Characterisation, pinned before anything moves:

- [x] The `claude-cli` route still refuses a non-Claude pin, a version without the transport tag, and a working directory inside the repository, and still passes the empty tool list.
- [x] The `bedrock-converse` route still requires its version tag and applies retry without pacing.
- [x] The `openai-compatible` route applies the same pacing and retry parameters as before.
- [x] Blind reports record the same `assessor_transport` strings as before.

Then:

- [x] Faithfulness calibration's private builder and the paced builder in grounding freeze are gone; every command calls the factory.
- [x] `harness/HARNESS.md`'s guardrail table points at the factory's policy table, and the subscription module's "what independence survives" account stays accurate.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5: blind-assessment command and assessor construction change).
- [x] `code-review` run since the base commit, with no gaps on the spec axis.

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

## Comments

- Deferred at Step 3 (2026-11-06): its misroute does not reach the blind assessment on either transport (W03 §3); ticket 12 gives the DN path an up-front refusal for an omitted --transport. Revisit after 01.
- Wave 2b (2026-11-06): order in `discovery/scope-cut-2026-11-06.md`; brief reads "at or above BASELINE.md §5" once wave 1 has merged.
- 2026-11-11, session (base `ac90a3a4`, branch `ticket/03-judge-factory`): targeted 64 modules, 3,145 passed, 1 failed (§5 baseline id `test_demo_candidate_blind_baseline.py::...::test_the_leakage_scan_file_count_is_re_derivable`), 13 skipped. Code review: spec axis found no missing or wrong requirement (judgement calls: the `claude-cli` route now requires a `claude_cli` environment; the two former lazy-default callers are refused on a Converse environment and gain retries; pacing characterisation covers blind assessment and the grounding freeze, rubric grading and faithfulness calibration only through the shared factory); standards axis found no hard violation (layering note: the factory lazily imports the two route backends from `harness/commands/`). `test_judge_factory.py` joined the isolation lane area. Full suite and lane not run.
- 2026-11-11: the operator confirmed the three behaviour changes in session: (1) `--transport claude-cli` requires a `claude_cli` environment; (2) the rubric grid helper and materiality calibration use the `openai-compatible` route and now retry; (3) an unknown route and pacing budgets on an unpaced route are refused.
