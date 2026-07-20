# Evaluation & Integrity Harness — substrate (E1)

> Out-of-band QA/CI track. **Never a fail-closed runtime gate.** Advisory to a
> human. Subordinate to `CLAUDE.md`.
>
> Source: `harness_plan/EVALUATION_HARNESS_STRATEGY.md` (v1),
> `harness_plan/tickets_eval_harness.md` (E1). Reviewed in
> `harness_plan/EVAL_HARNESS_TICKETS_REVIEW.md`.

This package (`harness/`) is the scaffolding every harness metric (E2–E9) stands
on. E1 builds **only the substrate** — the judge, provenance, routing, verdict
types, and reporting boundary. The metrics that use it (status-aware
faithfulness, claim-ledger completeness, the evaluator G-Evals, the α-block
assertion, graph-retrieval precision/recall) are later tickets.

## The one load-bearing invariant

**No eval metric wires into the runtime DAG as a fail-closed gate.** An
LLM-as-judge is stochastic and can be confidently wrong; putting one inside the
scheduler would break §17 byte-equal replay and the fail-closed contract. So:

- The **138 deterministic predicates + byte-equal CI checks remain the only
  blocking runtime gates.** The harness does not add, replace, or weaken any of
  them.
- The harness gates **decisions *about* the pipeline** — a PR that changes a
  drafting skill, a soft-cap lift, a model swap, a release cut — offline, in CI.
- Even there it is **advisory to a human**, not auto-blocking, **until judge
  reliability is characterized** (E1.5). A `HarnessReport` is `advisory=True,
  blocking=False` by construction and exposes no gate pass/fail the scheduler
  could consume.

### Three tiers (this harness is tier 3)

1. **Deterministic predicates** — hard, in-run, authoritative (the proof).
2. **In-run LLM review skills** — advisory, in-run, same model family.
3. **This harness** — independent, out-of-band, regression + adversarial.

The harness is tier 3. It does not preempt tier 1, and it deliberately
*re-checks* tier 2 with an independent model (an in-run reviewer cannot be the
unbiased grader of its own pipeline).

## The enforced boundary (structural, not just prose)

| Guardrail | Where it is enforced in code |
|---|---|
| Judge output is `Inferred`, never `Confirmed` | `verdict.py` — `Verdict` / `MajorityVerdict` reject any other `evidence_type`; `provenance.py` and the judge carry it through |
| Never a runtime gate / advisory-to-human | `report.py` — `HarnessReport(advisory=True, blocking=False)` cannot be constructed otherwise; no method returns a scheduler-consumable gate result |
| `harness` never becomes a runtime dependency | one-way import: `harness → runner` only; `tests/harness/test_boundary.py` asserts `runner` never imports `harness` |
| Deterministic-first routing | `routing.py` — a property named by a deterministic `PREDICATE_REGISTRY` function is refused for judging (`assert_judgeable` raises `DeterministicCoverageError`) |
| Grader–generator independence | `judge.py` — `JudgeConfig` rejects any drafter/in-run model; the default backend rejects the `claude_cli` transport, forcing the OpenAI-compatible path |
| Pin + determinism | `judge.py` — model + version pinned, temperature forced to 0; both recorded on every provenance record |
| No silent repair | `judge.py` — a malformed/empty judge response raises `JudgeResponseError`; the judge never guesses a verdict |
| Provenance for every verdict | `judge.py` builds a `ProvenanceRecord` for every `Verdict` and appends it to the attached `ProvenanceLog` before returning |

## Deterministic-first routing

The judge earns its place on exactly one axis the predicates provably cannot
reach: **semantic entailment**. For any property a predicate *can* check, the
predicate is authoritative and the judge must not run — re-implementing a
deterministic check as a judge trades a proof for a probabilistic opinion.

`routing.py` sources the deterministic set live from
`runner.gate_evaluator.PREDICATE_REGISTRY`, so it never drifts from what the
scheduler actually dispatches. The **semantic** in-run gates
(`semantic_dispatch.SEMANTIC_REGISTRY`, e.g. `no_unsupported_tier5_claims`) are
**not** treated as deterministic coverage — they are the same-model-family
judgments the harness legitimately re-checks with an independent model.

A metric therefore names its property by the *semantic question* the predicate
leaves open, under a key **distinct** from the predicate: e.g. the deterministic
`source_refs_present` (a field is non-blank) leaves open the semantic
`source_entails_claim` (the cited source actually supports the sentence). Routing
refuses the former and permits the latter.

## Judge configuration

- **Model + version pinned**, temperature 0 (`JudgeConfig`). A repin re-opens
  E1.5's advisory-only state, so both are logged on every verdict.
- **Non-drafter** model, over the **OpenAI-compatible transport** — never the
  `claude_cli` drafter transport. Independence is checked at both the config
  layer (model) and the backend layer (transport).
- Configured from `HARNESS_JUDGE_MODEL` / `HARNESS_JUDGE_VERSION` (see
  `resolve_judge_config`), pointed at a non-Claude backend via the standard
  `ORCHESTRATOR_TRANSPORT_*` variables (e.g. a `together_ai` or
  `openai_compatible` preset). The judge is **injectable** — pass a backend
  callable and no network/`httpx` is touched, which is how the substrate is
  unit-tested offline.

## N≥3 majority scaffold

Where a score will inform a decision, run the judge N≥3 times and combine via
`majority_vote`. At temp 0 the samples are near-identical; the panel exists to
absorb residual provider non-determinism and to surface genuinely borderline
properties via the `agreement` signal. A tie resolves conservatively to `False`
(integrity-weighted). The combined `MajorityVerdict` is still `Inferred`.

## Provenance

`ProvenanceLog` is an append-only JSONL sink written atomically (Python owns
every write, §9/§17.5.3). It is an **out-of-band artifact** — not a Tier 4 gate
result, and nothing in `runner` reads it. Every record carries the guardrail
five (`judge_model, judge_version, prompt_hash, score, rationale`) plus
supplementary context (metric, property_key, passed, sample_index, evidence_type,
timestamp).

## E1.5 — Judge-reliability calibration (the advisory → gating mechanism)

The guardrail says the harness stays advisory "until judge reliability is
characterized." E1.5 is that characterization — without it the clause has no
mechanism and the harness is advisory forever.

- **Human-labeled gold set** (`gold_set.py`) — `(claim, source_ref, supported?)`
  triples where `supported?` is a **human** ground truth, not the engine's
  `status` (the engine can stamp `confirmed` over an unsupported claim; that is
  the very error we calibrate against). The loader is **fail-closed**: an
  unlabeled pair cannot be used for calibration. `seed_pairs_from_claim_statuses`
  draws real candidates deterministically from a section's `claim_statuses` but
  never fabricates the label. A real seeded template lives in
  `harness/gold_sets/` (labels pending — see its README).
- **The atomic faithfulness question** (`faithfulness.py`) — asks the pinned
  judge "does this source support this claim?" (`passed=True` = supported). E2
  will extend this same question with status partitioning; E1.5 owns only the
  atomic unit the gold set is labeled against.
- **Precision/recall meta-eval** (`calibration.py`) — runs the judge over the
  labeled set, computes a confusion matrix (positive = `supported`, so a false
  positive = the judge blessed a gap — the integrity-critical error), and records
  `{judge_model, judge_version, precision, recall}` in a `CalibrationReport`.
- **Graduation** — `graduation_for(judge_config, report)` returns `advisory` or
  `gating_permitted` via a fail-safe cascade: no calibration → advisory; a
  **repinned** judge (model/version changed) → advisory; below the threshold →
  advisory; only a fresh, applicable, above-threshold calibration → gating
  permitted. Even then it clears a *human* to gate a merge — nothing blocks a
  run. The threshold (`GraduationThreshold`) is operator policy; the default is a
  conservative starting bar, not an endorsement.
- **Repin re-opens advisory-only** — a calibration is keyed to the exact judge it
  measured; change the model or version and the graduation it supported no longer
  applies. `CalibrationLog` keeps the history so the current judge's status is a
  lookup by model+version.

## What E1 / E1.5 do *not* do

- They do not compute any production metric (E2–E9). E1.5's `faithfulness.py` is
  the atomic calibration question, not E2's status-partitioned metric.
- They do not adopt Ragas / DeepEval / PromptFoo. Their exact metric/API names
  predate the knowledge cutoff and must be confirmed against current docs at
  build time (guardrail: API currency). Nothing here depends on them.
- They do not auto-gate a merge. E1.5 supplies the *mechanism* to graduate
  advisory → human-gating (`graduation_for`), but graduation still requires a
  human-labeled gold set and a judge that clears the operator's threshold; the
  seeded gold set ships **unlabeled**, so the harness remains advisory until a
  human labels it and re-runs calibration.
