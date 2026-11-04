# 07a — Skill response contract, part 1: parse and validate the response text

Status: needs-triage
Type: task
Blocked by: None — can start immediately
Source: `discovery/architecture-review-runtime-2026-11-03.html`, candidate B. Not grilled. The operator
accepted the recommendations on 2026-11-04, including the 07a/07b split.
Findings: F4 · plan §4 item 6

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

A new runtime module, the **skill response contract**, owns everything that happens to a skill's
response text after the transport returns it and before anything is written. In this ticket it takes
over the parse-and-validate half. Today that half is Phases D, D.5 and D.6 of `run_skill`
(`runner/skill_runtime.py` ~2024–2182) plus their helpers (~1086–1373: `_json_break_point`,
`_extract_json_response`, `_validate_skill_output`).

After this ticket, the module takes response text, the skill's catalog entry, the artifact schemas and
the `run_id`, and returns one of two results: a parsed, validated response ready to be written, or a
`SkillResult` failure. `run_skill` calls it once, straight after invocation. The write modes (Phase E)
stay in `run_skill` until 07b.

Parts of the interface:

- **JSON extraction.** It is the skill runtime's current policy, now public: the largest object wins,
  and front-truncation fails closed (`_json_break_point`).
- **Model-level failure signalling (D.5).** A model-emitted failure envelope becomes a `SkillResult` failure.
- **Success-envelope unwrapping (D.6).** It is unwrapped exactly as today.
- **The no-silent-repair rules (§17.5.4, §17.6.5).** A missing `run_id`, the wrong `schema_id`, or an
  `artifact_status` present in the response is a validation failure. Nothing is repaired or retried.

`runner/decomposed_drafting.py` (~line 693) stops importing the private `_extract_json_response` and
calls the public extractor.

## Decisions (operator accepted recommendations, 2026-11-04)

- **One module, two tickets.** The contract module is created here; 07b moves the write modes into
  it. With this split, `run_skill` keeps mode selection, prompt assembly and invocation (Phases A–C).
- **Size.** As a pure move this is about 450 lines, which is over the ~400 rule (§3.3). The operator
  decided that for a **pure move pinned by characterisation tests written beforehand**, the size rule
  is measured on net-new and changed logic, not on moved lines. Any behaviour change in this ticket
  falls back under the normal rule.
- **The extraction policy is kept as it is.** The largest object wins, and front-truncation fails closed.
- **The policy name.** The extractor gets a public name inside the contract module. `runner/json_extract.py` is not touched.

## Acceptance criteria

Characterisation tests first, written against today's `run_skill` (driven via
`runner.claude_transport.invoke_claude_text`, as the existing tests are), and passing before any move:

- [ ] Prose surrounds two JSON objects: the larger one is selected.
- [ ] Front-truncated JSON fails closed with today's failure category and reason shape.
- [ ] A missing `run_id`, the wrong `schema_id`, and an `artifact_status` present each fail, with no repair.
- [ ] A model-emitted failure envelope (D.5) becomes a `SkillResult` failure with today's category.
- [ ] A SkillResult-shaped success envelope (D.6) is unwrapped and validated as today.

Then:

- [ ] The same behaviours are tested directly at the new interface: text in, result out, with no transport stub. Tests that only exercised the removed private helpers are deleted once an interface test covers them (replace, don't layer).
- [ ] `decomposed_drafting` imports only public names from the contract module. `grep _extract_json_response runner/` matches only that module, or nothing.
- [ ] `run_skill` keeps its signature and its `SkillResult` contract (§17.4.1). `tests/runner/test_skill_runtime*.py`, `test_decomposed_drafting_transport.py`, `test_excellence_decomposed_drafting.py` and `test_impact_implementation_decomposed_drafting.py` stay green, unedited except for removed-internal patches.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

No PE-09 run: nothing under `transport/` or the DN pre-evaluation paths changes (admission rule 5 does not apply).

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/07a-skill-response-contract-parse-validate.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17 (esp. §17.4.1, §17.5.4, §17.6.5), CONTEXT-MAP.md (+ runner/CONTEXT.md),
            docs/agents/*.md, plans/overhaul/BASELINE.md, plans/reports/RUNTIME_MAP.md
Seam: skill response contract (new runtime module) — interface before: none (Phases D–D.6 inline in
      run_skill, private _extract_json_response borrowed by decomposed_drafting); after: one public
      call taking response text + skill entry + schemas + run_id → validated response | SkillResult failure
Do not touch: §17 call graph, run_skill signature, Phases A–C and E, runner/json_extract.py,
      claude_transport.py, transport/, agent_runtime.py, gate_evaluator, Tier 1–3 docs
Tests first: the five characterisation tests above (tdd / characterisation, before any move)
Size: ~450 moved lines, net-new logic small — pure move under the operator's 2026-11-04 size rule
Skills: tdd, codebase-design, code-review
Record: no decision-log entry (no orchestration interpretation changes)
```

## Out of scope

- Making the two JSON-extraction policies consistent. The shared `runner/json_extract.py` (first
  object, no front-truncation guard) is used by `semantic_dispatch` and the harness judge. Unifying the
  two policies changes behaviour, so it is a separate operator decision.
- The write modes (07b). Transport and backend selection (09).
