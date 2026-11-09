# 15 — A resume is honest: same inference configuration, replays recorded as replays (UR-B)

Status: ready-for-agent
Type: task
Blocked by: 10, 12
Source: `discovery/ultrareview-run-path-2026-11-04.md` findings 6 and 5 (5 moved here from deferred ticket 01)
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F6 · DN run path (V14 requires `--resume`)

## What to build

Resuming a blind assessment either reproduces the interrupted run's inference configuration exactly or
refuses, and the provenance trail tells replayed draws from live ones. Today:

- the checkpoint binding claims to carry "the sampling parameters" but holds only `n` and
  `criterion_samples`. Replay is keyed by prompt hash, so a resume after a change of temperature or token
  limit is accepted and one report mixes two inference configurations (finding 6);
- a resumed run writes a new provenance record, with a fresh timestamp and no replay mark, for every
  replayed checkpoint response, so the trail counts replays as live draws (finding 5).

## Decisions (scope cut, 2026-11-06)

- **The binding covers the inference configuration:** temperature and the token limit join the binding
  (with the assessor pin already there). A mismatch on resume is refused, naming the field and both values.
- **Old checkpoints:** a checkpoint written before this change, with no such fields, still opens; a resume
  of it is refused with a message saying the configuration was not recorded. No old checkpoint is in use
  for V14/V16 (both start after the 10 Nov freeze).
- **Replays:** a replayed response writes no new live provenance record, or a record marked replayed; the
  report's `replayed_calls` / `live_calls` counts stay correct. This is the minimal fix, not ticket 01's
  redesign.

## Acceptance criteria

Failing tests first:

- [ ] Resume with a different temperature: refused, naming the field and both values.
- [ ] Resume with a different token limit: refused likewise.
- [ ] Resume with an identical configuration: replays exactly as today.
- [ ] A resumed run's provenance log holds no unmarked records for replayed responses; live draws are unchanged.
- [ ] A pre-change checkpoint opens; resuming it is refused with the not-recorded message.

Then:
- [ ] **PE-09 acceptance lane green**, run with ticket 10's lane (admission rule 5).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/15-a-resume-is-honest.md   Base commit: <sha after 10 and 12 merged>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md,
            .scratch/overhaul-2026-11/discovery/ultrareview-run-path-2026-11-04.md
Seam: the response-checkpoint binding and the judge's replay path — no public interface change
Do not touch: the judge-call redesign (ticket 01, deferred), freeze conditions, runner/transport/*, Tier 1–3 docs
Skills: diagnosing-bugs, then tdd
Size: ~60–120 changed non-test lines
Record: none
```

## Out of scope

- Uniform redraw, discarded draws in the report (ticket 01, after V16).
- The rubric lane's checkpoint (ticket 02, deferred).
