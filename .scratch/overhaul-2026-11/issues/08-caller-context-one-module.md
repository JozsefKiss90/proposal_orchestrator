# 08 — Caller context: one module answers "what does this skill get here?"

Status: needs-triage
Type: task
Blocked by: None — can start immediately
Source: `discovery/architecture-review-runtime-2026-11-03.html`, candidate C. Not grilled. The operator
accepted the recommendations on 2026-11-04, including both loops in scope.
Findings: F4

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

One module in the agent runtime decides the caller context a skill receives at a given point in a node
body. It returns one of three outcomes:

- **context** (a dict, possibly empty for a skill that declares no need);
- **not applicable**, with a reason (the skill is skipped and recorded as `not_applicable`);
- **missing**, with a reason (the skill is not invoked and fails as `MISSING_INPUT`).

Both skill loops in `run_agent` call it, and act only on the answer.

Today the decision is spread across `runner/agent_runtime.py` (line numbers at HEAD `5ba39e2d`):

- the `_build_caller_context` registry (~836) with `_context_sources_for` / `_missing_context_sources` and the "no declared source resolved" fail-closed guard (main loop ~1584–1631);
- the Tier-5 applicability guard `_check_skill_applicability` (~1566);
- five inline special cases at **two** sites:

| # | Skill | Injected | Site | Today's fail-closed |
|---|-------|----------|------|---------------------|
| 1 | budget-interface-validation | `invocation_mode` | **pre-gate loop** (~1404–1418) | none: the pre-gate loop bypasses the registry and the guard |
| 2 | budget-interface-validation | `invocation_mode` | main loop (~1634) | registry guard only |
| 3 | gate-enforcement | `gate_id` from the node's exit-gate binding | main loop (~1640) | none if no exit gate (context passed without it) |
| 4 | instrument-schema-normalization | `resolved_instrument_type` from `selected_call.json` | main loop (~1650) | own inline `MISSING_INPUT` |
| 5 | constitutional-compliance-check, proposal-section-traceability-check | `artifact_path` from outputs so far, plus the non-Tier-5 skip for traceability | main loop (~1687–1765) | own inline `MISSING_INPUT` / `not_applicable` |

The handoff listed four cases at one site. Case 1 is the extra one.

## Decisions (operator accepted recommendations, 2026-11-04)

- **One table of bindings.** Each special case becomes a row (skill → how to resolve the value → what an
  unresolvable value means). The registry sources become rows of the same kind. Adding a skill becomes
  one row.
- **Both loops.** The pre-gate loop asks the same module, so the fail-closed rule covers it too.
- **Fail-closed covers every binding.** "Missing" is decided in one place for all rows. The registry
  guard keeps its current scope: it fails only when *no* declared source resolved, and a partial
  context still warns and passes.
- **No behaviour change unless pinned first.** Where moving a case makes it stricter (the pre-gate
  path gaining the guard, or gate-enforcement with no exit gate), the new behaviour gets a failing
  test first, and the ticket records whether it actually changes for any manifest node at HEAD.
- **Outputs so far** are an input to the module, so the `artifact_path` row stays order-dependent
  exactly as today. Node-body ordering itself is not touched (candidate D, deferred).

## Acceptance criteria

Characterisation tests first, before anything moves. This is the area of the 2026-08-13 fail-closed
guard and the Phase 3 g04_p07 missing-binding failure, so pin today's behaviour for every case above:

- [ ] budget-interface-validation gets `invocation_mode` in the **pre-gate** loop, and again in the main loop.
- [ ] gate-enforcement gets the node's exit gate as `gate_id`. Today's behaviour for a node with no exit gate is pinned.
- [ ] instrument-schema-normalization: a resolvable `selected_call.json` gives the type, and missing or malformed fails `MISSING_INPUT` without invoking the skill.
- [ ] constitutional-compliance-check: an auditable artifact gives `artifact_path`, and none fails `MISSING_INPUT`.
- [ ] proposal-section-traceability-check: a Tier-5 artifact gives `artifact_path`, a Tier-4 artifact gives `not_applicable`, and none fails `MISSING_INPUT`.
- [ ] A registry skill with all declared sources absent fails `MISSING_INPUT` uninvoked. With some present it warns and passes.
- [ ] The Tier-5 applicability guard skips audit skills before Tier 5 exists.

Then:

- [ ] Any stricter behaviour (see Decisions) has a failing test first, and a note in this ticket.
- [ ] The module is tested as a pure function (skill, node, resolved inputs, outputs so far, repo root → outcome) with no `run_skill` stub. Existing `tests/runner/test_caller_context.py` and `test_agent_runtime.py` stay green. Tests that only patched removed internals are replaced by interface tests.
- [ ] Neither loop in `run_agent` contains a skill-name comparison for context any more.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.
- [ ] A decision-log entry, only if a stricter behaviour actually changes a node's outcome (§9.4).

No PE-09 run (admission rule 5 does not apply).

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/08-caller-context-one-module.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17 (esp. §17.1.2, §17.5.3), CONTEXT-MAP.md (+ runner/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, tests/runner/test_caller_context.py
            (Claude project memory, if readable: caller-context-bindings.md)
Seam: caller context (new module inside the agent runtime) — interface before: _build_caller_context
      registry + guard + five inline skill-name cases across two loops; after: one call →
      context | not applicable | missing
Do not touch: §17 call graph, run_agent's signature and AgentResult, node-body ordering (pre-gate split,
      gate-enforcement-last, n03 sub-agent, reuse/supersession skips), skill_runtime.py, run_skill's
      caller_context handling, manifest/catalog YAML, gate_evaluator, Tier 1–3 docs
Tests first: the seven characterisation tests above, then failing tests for any stricter behaviour
Size: ~300 lines moved, ~100 net-new (the table and outcome type)
Skills: tdd, codebase-design, code-review
Record: decision-log entry only if a node's outcome changes
```

## Out of scope

- Node-body plan and ordering (candidate D, deferred past 23 Nov).
- Tightening the registry guard from "none resolved" to "any missing".
- How `run_skill` puts caller context into the prompt (TAPM and cli-prompt).
