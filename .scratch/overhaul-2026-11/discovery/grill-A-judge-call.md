# Grill record — A · Deepen the judge call (harness/)

Date: 2026-11-03 · Base: `harness_overhaul` @ `d1e8527f`
Source: `architecture-review-harness-2026-11-03.html`, candidate A (Strong, F5, DN critical path).
Status: **shared understanding confirmed by operator**. Input to Step 3 scope cut and `to-tickets`.
Vocabulary: `harness/CONTEXT.md` (Judge, Assessor, Draw, Discarded draw, Candidate, Blind report).

## Facts established (looked up, not decided)

- Three call paths today:
  - `evaluate` / `evaluate_majority` (faithfulness, status faithfulness, materiality, status
    calibration, expectation coverage → blind-assessment cells, claim-ledger checks):
    a malformed draw is discarded from the checkpoint, then the run stops.
  - `raw_invoke` + criterion scoring's loop: discarded and redrawn in-run, up to 2 times;
    recorded as `DiscardedDraw` on the score.
  - `raw_invoke` + claim-ledger decomposition: **not discarded, not redrawn**; provenance hand-built.
- The salvage command writes transcripts straight into the checkpoint with a looser rule
  ("any JSON object") than the cell parser.
- `ResponseCache.discard_last` works on a replayed draw as well as a live one.
- `load_report` ignores unknown fields; `BASELINE_CHECKS` (freeze schema 1.2.0) has no check on discarded draws.
- No hand-written fake judges in tests; all build a real `Judge` with an injected backend.

## Decisions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Who owns the in-run redraw? | **The judge, the same for every call.** Bounded budget set on the judge (default 2), discarded draws recorded, fail closed on exhaustion. In a majority vote of n, a redraw *replaces* the malformed sample, so there are still n votes. |
| Q2 | What signals "malformed, redraw"? | **Only `JudgeResponseError`** from the parser. Any other exception passes through with no redraw. The claim-ledger decomposition parser switches from `ClaimLedgerError` to `JudgeResponseError` (6 test expectations change; `ChunkFailure` handling is unaffected). |
| Q3 | Who writes provenance? | **The judge writes all of it.** The parsed value reports its own `score` / `passed` / `rationale` through a small protocol. The hand-built records in criterion scoring and claim-ledger decomposition go. `DiscardedDraw` moves into the judge and comes back on every result. |
| Q4 | Do discarded draws appear in the DN blind report? | **Yes, as an additive field, with no new check.** Every cell gets `discarded_draws` (same shape as criterion scores), and the report summary gets a total next to `replayed_calls` / `live_calls`. Old reports and frozen baselines still load (missing = none recorded). Freeze conditions and the PE-09 runbook are unchanged. |
| Q5 | What happens to `evaluate`, `evaluate_majority` and `raw_invoke`? | **`ask` is the one place requests go out; the others stay as presets on top of it.** `evaluate` = `ask` + `parse_verdict`; `evaluate_majority` = n × `ask` + `majority_vote`; the 8 callers don't change. `raw_invoke` becomes the private `_send`, and the transport tests move to it. |
| Q6 | How does salvage decide which transcripts are usable? | **The same verdict parser the run uses.** Extraction plus `_verdict_from_payload` become a public `parse_verdict`. A replayed draw that fails parsing uses budget and is marked `replayed: true`. |
| Q7 | One ticket or two? | **One ticket.** About 250–350 changed non-test lines; no window where cells redraw invisibly. |

## Resulting design

`Judge.ask(system, user, parser, *, metric, property_key)`, in order inside:
checkpoint lookup or record (`_send`) → strict parse → on `JudgeResponseError`: discard from the
checkpoint and redraw (bounded) → fail closed when the budget is spent → write provenance → return
the value, its provenance and its discarded draws.

## Ticket shape

- Files: `harness/judge.py`, `criterion_scoring.py`, `claim_ledger.py`, `expectation_coverage.py`,
  `blind_assessment.py`, `commands/blind_assessment.py` (+ tests).
- Admission: one seam (judge interface) · behaviour change is the point (failing tests first) ·
  fits one session · no constitutional amendment · **rule 5 applies → PE-09 acceptance lane green**.
- §17 call graph unchanged; harness → runner import direction unchanged.

## Failing tests first (in order)

1. A cell gets a malformed draw, then a valid one: it succeeds with one `discarded_draw`.
2. Decomposition gets a malformed draw: it is discarded from the checkpoint, redrawn, and provenance is written by the judge.
3. A non-`JudgeResponseError` from a parser passes through with no redraw.
4. A majority vote with one redraw still produces exactly n verdicts.
5. A replayed malformed draw uses budget and is marked `replayed: true`.
6. Salvage counts JSON that is not a valid verdict as malformed.
7. An old report without `discarded_draws` still loads and freezes.

## Out of scope (carried to Step 3)

- Making the two JSON-extraction rules consistent (skill runtime's front-truncation guard vs the shared
  `extract_first_json_object`) — runtime review, cross-finding.
- Judge construction and the independence policy — harness review, candidate B.
- Any freeze check on redraw counts.

## Side effects

- `harness/CONTEXT.md`: added **Draw** and **Discarded draw**.
