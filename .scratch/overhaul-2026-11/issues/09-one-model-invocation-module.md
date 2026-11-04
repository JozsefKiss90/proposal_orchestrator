# 09 — One model-invocation module behind the transport seam

Status: needs-triage
Type: task
Blocked by: 07a, 07b
Source: `discovery/architecture-review-runtime-2026-11-03.html`, candidate A. Not grilled. The operator
accepted the recommendations on 2026-11-04.
Findings: F4 · F5 · admission rule 5 (`transport/`)

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

One runner module chooses and calls the model backend. It takes a provider-neutral request and returns
a provider-neutral response. Today the work of the provider switch (build backend → instrument → call →
map errors → empty-text check) is written out in three blocks:

- `run_skill`, TAPM branch (`runner/skill_runtime.py` ~1538–1820): claude CLI · Bedrock Converse + tool loop · OpenAI-compatible + tool loop;
- `run_skill`, cli-prompt branch (~1839–2020): claude CLI · Converse · OpenAI-compatible;
- `semantic_dispatch._invoke_via_backend` (~613–690): claude CLI · Converse · OpenAI-compatible.

Each block copies the benchmark tags, timeouts and error class, so a fix to one (a timeout, the
empty-content check, tool-loop exhaustion) doesn't reach the others.

After this ticket:

- **Request:** system prompt, user prompt, optional tools and allowed path prefixes, timeout, benchmark tags.
- **Response:** text, files read, and whether tool-loop rounds were exhausted.
- **Failure:** one failure type, carrying a category the callers can map.
- **Adapters:** claude CLI (wrapping today's `invoke_claude_text`), Bedrock Converse (+ tool loop),
  OpenAI-compatible (+ tool loop), and an in-memory adapter for tests.
- **Callers:** `run_skill` (both prompt modes) and `semantic_dispatch._invoke_via_backend` call it,
  and keep mapping the one failure type to their own categories (`SkillResult` /
  semantic-dispatch failures) exactly as today.

## Decisions (operator accepted recommendations, 2026-11-04)

- **This is the configured transport.** The §17.1.3 call graph is unchanged: the skill runtime still
  reaches Claude only through it, and so does semantic dispatch.
- **Interface shape** as above. Before writing code, the implementer runs `codebase-design`'s
  design-it-twice step. Two or more request/response shapes are compared in prose in this ticket's
  `## Comments`, and the operator confirms the choice, before any move.
- **Both prompt modes stay.** Candidate E (retire cli-prompt) was **not** taken on 2026-11-04. Three live
  catalog skills, including `budget-interface-validation` at n07, run in cli-prompt by default. The
  adapter matrix therefore covers both modes. See `discovery/decision-E-tapm-banner-2026-11-04.md`.
- **Runner side only.** Runner code never imports harness code. Harness ticket 03 may later adopt this
  module as a judge adapter (harness → runner only).
- **Benchmark instrumentation** (`runner/benchmark/transport_hook.py`) wraps the adapters at one place,
  instead of being applied per block. Recorded tags must stay byte-identical to today's.
- **Blocked by 07a/07b.** Both restructure `run_skill`. Once the contract has landed, this ticket only
  replaces the invoke blocks.

## Acceptance criteria

Characterisation tests first, per backend × caller, before any move:

- [ ] TAPM × {CLI, Converse, OpenAI-compatible}: text returned, files read recorded, and rounds-exhausted behaviour pinned.
- [ ] cli-prompt × {CLI, Converse, OpenAI-compatible}: text returned. The empty-content check and the timeout failure each give today's `SkillResult` category.
- [ ] semantic dispatch × {CLI, Converse, OpenAI-compatible}: text returned, with today's error mapping.
- [ ] The tool-calling capability gate (a non-CLI backend without tool calling in TAPM) fails as today.
- [ ] The benchmark tags recorded per invocation are identical before and after.

Then:

- [ ] The module is tested through its interface with the in-memory adapter and with each real adapter's
      backend stubbed. Most runtime tests no longer patch `runner.claude_transport.invoke_claude_text`;
      they inject the in-memory adapter. Tests that only patched removed internals are replaced.
- [ ] There is no provider switch left in `skill_runtime.py` or `semantic_dispatch.py`.
- [ ] `tests/runner/test_skill_runtime*.py` (incl. `_tool_loop`, `_tapm`), `test_claude_transport*.py`,
      `test_semantic_dispatch.py`, `test_decomposed_drafting_transport.py` and `tests/runner/benchmark/`
      stay green.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5: touches `transport/`).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/09-one-model-invocation-module.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17 (esp. §17.1.3, §17.5.2, §17.5.4), CONTEXT-MAP.md (+ runner/CONTEXT.md),
            docs/agents/*.md, plans/overhaul/BASELINE.md, plans/reports/RUNTIME_MAP.md,
            discovery/decision-E-tapm-banner-2026-11-04.md
            (Claude project memory, if readable: transport-continuation-splice.md, transport-cli-pin.md,
            runner-model-pin.md)
Seam: model invocation (the configured transport) — interface before: three inline provider switches
      in run_skill ×2 and semantic_dispatch; after: invoke(request) → response | one failure type,
      with CLI / Converse / OpenAI-compatible / in-memory adapters
Do not touch: §17 call graph, run_skill / invoke_agent signatures, prompt assembly, the skill response
      contract (07a/07b), runner/json_extract.py, harness/, model pins, CLI pin, gate_evaluator,
      skill_catalog.yaml, Tier 1–3 docs
First step: codebase-design design-it-twice on the request/response shape → operator confirms
Tests first: the five characterisation groups above
Size: ~450 lines leave run_skill, plus ~100 from semantic_dispatch; net-new ~250 (module + adapters + fake)
Skills: codebase-design, tdd, code-review
Done when: as above, incl. PE-09 acceptance lane green
Record: no decision-log entry unless a failure category mapping changes
```

## Out of scope

- Retiring cli-prompt mode (candidate E, not taken).
- Unifying the JSON-extraction policies.
- Harness judge builders adopting this module (harness ticket 03).
- Changing model or CLI pins.
