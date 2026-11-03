# 01 — Deepen the judge call: one `ask`, parser in, verdict out

Status: needs-triage
Type: task
Blocked by: None — can start immediately
Source: `discovery/grill-A-judge-call.md` (operator-confirmed 2026-11-03) · `discovery/architecture-review-harness-2026-11-03.html`, candidate A
Findings: F5 · DN critical path

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

Every judge draw in the harness goes through one judge interface that takes a prompt and a strict
parser and hands back a parsed value with its provenance and its discarded draws. Before this ticket,
a malformed draw has three outcomes: the run stops (verdicts and blind-assessment cells), it is redrawn
(criterion scores), or it is neither discarded nor redrawn (claim-ledger decomposition). After it, a
malformed draw is handled the same way everywhere:

1. It is discarded from the response checkpoint.
2. It is redrawn over the identical prompt within a bounded budget set on the judge (default 2).
3. It is recorded as a discarded draw.
4. It fails closed once the budget is spent.

The operator can see every discarded draw in the DN blind report. The salvage command judges
transcripts with the same verdict parser the run uses.

## Decisions this ticket implements (Q1–Q7 of the grill record)

- **Redraw.** It is owned by the judge and the same for every call. In a majority vote of n, a
  redraw replaces the malformed sample, so there are still n votes. A replayed draw that fails parsing
  uses budget and is marked `replayed`.
- **Malformed.** Only `JudgeResponseError` from the parser means "malformed, redraw". Any other
  exception passes straight through. Claim-ledger decomposition's parser now raises
  `JudgeResponseError`.
- **Provenance.** The judge writes every record. The parsed value reports its own score / passed /
  rationale through a small protocol. The hand-built records in criterion scoring and claim-ledger
  decomposition are removed. Discarded draws are a judge concept, returned on every result.
- **Interface.** The prompt-and-parser call is the only way a draw goes out. `evaluate`
  (the verdict parser) and `evaluate_majority` (n × that call + majority vote) stay as presets, and
  their callers don't change. The raw single-draw call becomes private.
- **Blind report.** Every cell carries `discarded_draws`, and the report summary carries a total
  next to `replayed_calls` / `live_calls`. This is additive: no new freeze check, and the PE-09
  runbook is unchanged.
- **Salvage.** Salvage counts and discards transcripts with the shared verdict parser, not "any JSON
  object".

## Acceptance criteria

Failing tests first, in this order:

- [ ] A cell gets a malformed draw, then a valid one: it succeeds with exactly one discarded draw recorded on the cell.
- [ ] Claim-ledger decomposition gets a malformed draw: it is discarded from the checkpoint and redrawn, and its provenance record is written by the judge.
- [ ] A parser raising anything other than `JudgeResponseError` propagates with no redraw and no discard.
- [ ] A majority vote with one redraw still yields exactly n verdicts.
- [ ] A replayed malformed draw uses redraw budget and is marked `replayed`.
- [ ] Salvage counts a transcript holding JSON that is not a valid verdict as malformed.
- [ ] A blind report written before this change, without `discarded_draws`, still loads, verifies and freezes.

Then:

- [ ] Budget exhaustion fails closed with the parser's last message and the draw count; nothing is repaired.
- [ ] No harness module outside the judge calls the raw single-draw method.
- [ ] Criterion scoring's own redraw loop and its hand-built provenance are gone; behaviour is pinned by its existing tests.
- [ ] `harness/HARNESS.md` describes the one call path and the redraw rule.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5: blind-assessment code changes).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/01-deepen-the-judge-call.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/grill-A-judge-call.md
Seam: the harness judge — interface before: evaluate / evaluate_majority / raw_invoke (public);
      after: one prompt-and-parser call (public) + evaluate / evaluate_majority presets; raw draw private
Do not touch: §17 call graph, runner/ (harness → runner import direction only), gate_evaluator,
      Tier 1–3 docs, blind-baseline freeze conditions, judge construction / independence (ticket candidate B)
Tests first: the seven listed above, in order (tdd)
Size: ~250–350 changed non-test lines
Record: no decision-log entry needed (harness is out-of-band; no orchestration interpretation changes)
```

## Out of scope

- Making the two JSON-extraction rules consistent (runtime review cross-finding).
- Judge construction and the independence policy (harness candidate B).
- Any freeze check on redraw counts.
