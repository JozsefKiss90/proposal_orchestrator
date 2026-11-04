# 07b — Skill response contract, part 2: the four write modes

Status: needs-triage
Type: task
Blocked by: 07a
Source: `discovery/architecture-review-runtime-2026-11-03.html`, candidate B. Not grilled. The operator
accepted the recommendations on 2026-11-04.
Findings: F4 · plan §4 item 6

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

The skill response contract module (created in 07a) takes over Phase E of `run_skill`
(`runner/skill_runtime.py` ~2182–2729) and `_atomic_write`. After this ticket the module goes from
response text to a finished `SkillResult`, with artifacts written atomically. `run_skill` keeps mode
selection, prompt assembly and invocation, and delegates everything after the transport returns.

The write mode is chosen by the catalog's `output_contract`, never inferred. There are **four** modes
(at HEAD `5ba39e2d` the catalog has 5 single, 5 multi, 2 enrich and 2 payload entries):

| Mode | What it writes |
|------|----------------|
| `single_artifact` (default) | the validated response to its one canonical path |
| `multi_artifact` | each schema-matched sub-object, validated independently, to its own path |
| `enrich_artifact` | a merge into `enrichment_base_artifact` |
| `payload` | no canonical artifact; checks `payload_required_fields` and `run_id`, returns `SkillResult.payload`, and writes any embedded `decision_log_entry` to `docs/tier4_orchestration_state/decision_log/` with a sanitised file name |

## Decisions (operator accepted recommendations, 2026-11-04)

- **Four modes, not three.** The handoff and the report missed `payload`. It is in scope here, because it
  writes decision-log files and is the path gate-enforcement uses.
- **Size.** About 600 moved lines. The same 2026-11-04 rule applies as for 07a: a pure move pinned by
  characterisation tests is measured on net-new logic.
- **Python owns writes.** Every write still goes through the one atomic-write helper, which now lives in
  the contract module. Its existing callers outside `skill_runtime`, if any, import it from there.
- **Skill writes only.** The module never writes gate results (§17.6.3), and the decision-log write
  stays limited to the payload's embedded entry, as today.

## Acceptance criteria

Characterisation tests first, written against today's `run_skill` and passing before any move:

- [ ] `single_artifact` writes exactly one file at the canonical path, and its content equals the validated response.
- [ ] `multi_artifact` writes one file per matched schema. Today's partial-failure behaviour is pinned (which files exist, and which `SkillResult` comes back).
- [ ] `enrich_artifact` with a missing `enrichment_base_artifact` fails with today's category. With a base present it merges exactly as today.
- [ ] `payload` returns the payload without writing a canonical artifact. A missing required field, or a `run_id` mismatch, gives `MALFORMED_ARTIFACT`. A `decision_log_entry` whose `decision_id` holds colons is written under its sanitised name.
- [ ] A failed atomic write leaves no partial file and gives today's failure.

Then:

- [ ] The same behaviours are tested at the contract interface with a tmp dir (text in, files and `SkillResult` out), and `run_skill` is no longer needed to reach them. Tests covering only removed internals are replaced, not layered.
- [ ] `run_skill` from the end of invocation onwards is one call into the contract module. `tests/runner/test_skill_runtime*.py` (incl. `_enrich`) stays green.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

No PE-09 run (admission rule 5 does not apply).

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/07b-skill-response-contract-write-modes.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17 (esp. §17.4.1, §17.6.3, §17.6.5), CONTEXT-MAP.md (+ runner/CONTEXT.md),
            docs/agents/*.md, plans/overhaul/BASELINE.md, ticket 07a and its merged module
Seam: skill response contract — interface before (after 07a): text → validated response | failure;
      after: text + skill entry + schemas + run_id + repo root → SkillResult, artifacts written atomically
Do not touch: §17 call graph, run_skill signature, Phases A–C, runner/json_extract.py, claude_transport.py,
      transport/, agent_runtime.py, gate_evaluator, skill_catalog.yaml, Tier 1–3 docs
Tests first: the five characterisation tests above, before any move
Size: ~600 moved lines, net-new logic small — pure move under the operator's 2026-11-04 size rule
Skills: tdd, codebase-design, code-review
Record: no decision-log entry (no orchestration interpretation changes)
```

## Out of scope

- Changing which mode a skill uses, or any `skill_catalog.yaml` edit.
- Unifying the JSON-extraction policies (see 07a).
