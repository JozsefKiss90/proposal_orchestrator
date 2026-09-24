# Evaluation & Integrity Harness — substrate (E1/E1.5), the two headline signals (E2, E3) + the regression golden-set (E4)

> Out-of-band QA/CI track. **Never a fail-closed runtime gate.** Advisory to a
> human. Subordinate to `CLAUDE.md`.
>
> Source: `harness_plan/EVALUATION_HARNESS_STRATEGY.md` (v1),
> `harness_plan/tickets_eval_harness.md` (E1, E1.5, E2, E3, E4). Reviewed in
> `harness_plan/EVAL_HARNESS_TICKETS_REVIEW.md`.

This package (`harness/`) is the scaffolding every harness metric (E2–E9) stands
on. E1 builds the **substrate** — the judge, provenance, routing, verdict types,
and reporting boundary; E1.5 the judge-reliability calibration; **E2 and E3 the
two headline integrity signals** (status-aware faithfulness and claim-ledger
completeness + status calibration, below); **E4 the regression golden-set** that
freezes the current sections so a prompt/model change cannot silently regress
them. The remaining metrics (the evaluator G-Evals, the α-block assertion,
graph-retrieval precision/recall) are later tickets.

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
| `harness` never becomes a runtime dependency | one-way import: `harness → runner` only; `tests/harness/test_boundary.py` asserts `runner`, `tools/` and `scripts/` never import `harness`. The judge runners (E1.5 calibration, E4 grounding freeze, E5f rubric grading) therefore live in `harness/commands/` and run as `py -3.10 -m harness.commands.<name>` |
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

## E2 — Status-aware faithfulness (headline signal #1)

The first production metric, and the independent net M3's composition pass calls
for. It partitions every Tier-5 claim by the engine's own `status` and judges
each against the target that status *promises*, because a predicate can only see
that a `source_ref` field is non-blank — never whether the source actually
supports the sentence:

- **`confirmed` → judged strictly against its `source_ref`.** A confirmed claim
  must be directly evidenced (faithfulness ≈ 1.0); one its own source does not
  support is a **hard integrity finding** (`SEVERITY_INTEGRITY`) — the "gap
  masked as confirmed" no predicate can catch.
- **`assumed` → judged against the operator-declared value** in
  `working_assumptions.json` (via the shared `runner.working_assumptions` reader,
  by `key` then `checklist_ref`), **not** the source. This complements the W1
  predicate — W1 checks the declaration *exists*, E2 checks the claim faithfully
  represents its *content*. A mismatch is `SEVERITY_CONTENT_DRIFT`.
- **`inferred` → judged as framing/synthesis** against its source under a
  **softer** bar (`passed` *or* a score clearing a low `min_score`): a faithful
  inference need not be verbatim, but must not contradict or over-reach its
  source. A failure is a soft concern (`SEVERITY_SOFT`), not a hard finding.

It is a **custom metric on the E1 substrate — no framework dependency.** It
reuses `harness.judge.Judge` (pinned, non-drafter, provenance-logged),
`assert_judgeable` (a claim id colliding with a predicate name is refused),
`Verdict` (typed `Inferred`), and `build_report` (`advisory=True,
blocking=False`). The framework pick is recorded in the decision log
(`e2-status-aware-faithfulness-framework_2026-07-20.json`): **DeepEval/Ragas
adoption is deferred to E5 (G-Eval) / E8 (DeepTeam) / E9 (Ragas retrieval)** —
the lanes where a framework *primitive* is irreplaceable — because E2's claims
arrive pre-decomposed (`claim_statuses`), the substrate is deliberately
framework-independent and offline-testable, and the API-currency guardrail blocks
a real binding until the current API is confirmed. This is earn-its-lane:
*defer cost, demand proof.*

Un-verifiable claims are **surfaced, never dropped**: an unresolvable
`source_ref`, or an `assumed` claim with no backing declaration, becomes a
`SEVERITY_UNRESOLVED` finding with the judge *not* invoked; an unpartitioned
status becomes `SEVERITY_UNKNOWN_STATUS`. Reporting-only; zero DAG runs; built
against the current `*_section.json` and re-points at M2-T10's graph-sourced
artifacts unchanged (identical claim schema).

**M3 reuse — grounding invariance.** `freeze_baseline` snapshots the per-claim
grounding verdict on the pre-composition ledger; `compare_to_baseline` re-runs on
the composed output and flags any claim whose grounding **weakened** — a
`bar_regression` (met the bar, no longer does), a `status_changed`, or a
`dropped` claim all *break* invariance; a `score_drop` that still meets the bar is
a soft, non-breaking flag. *Form may change, grounding may not.* A baseline is
keyed to the judge pin it was frozen under (`applies_to`), so a comparison
spanning a repin is flagged (`judge_repinned`), mirroring the E1.5 discipline.

## Claim identity — `entry_key`, because `claim_id` is not a key

Real ledgers concatenate independently-numbered drafting blocks, so
`claim_id` repeats across **unrelated** claims (excellence: 191 entries / 128
unique ids; three different `C01`s) and nothing tags a claim to its
sub-section. Every harness surface therefore keys claims by
**`entry_key`** — `claim_id` disambiguated by its position in
`claim_statuses` (`C01#171`): the judge `property_key`/provenance, E2's
`hard_finding_ids`, the M3 baseline (`by_id()` would otherwise silently
collapse 191 snapshots to 128 and mis-compare), and every E3 record. E3's
matching goes further: it never matches by id at all — the ledger is treated
as a set of `(claim_summary, status, source_ref)` records matched by meaning,
and ids are display labels only.

## E3 — Claim-ledger completeness + status calibration (headline signal #2)

The "escaped claim" detector (`claim_ledger.py`) plus label-drift
(`status_calibration.py`), with the §10.5 materiality bar (`materiality.py`)
in between. All native on the substrate (the framework question re-opened at
E3 per the ticket and closed native again — decision log
`e3-claim-ledger-completeness_2026-07-21.json`).

- **The escaped claim (hard finding).** Prose is chunked deterministically
  (whole paragraphs), decomposed by the judge into atomic assertions
  (*exhaustively* — materiality is deliberately a separate classifier), and
  every **material** assertion is matched against the ledger by meaning:
  a deterministic lexical shortlist, then one **batched** judge call over
  numbered candidates (the judge answers with a candidate *number*, never an
  ambiguous claim id), escalating to the stricter per-candidate boolean
  question when coverage is asserted but unattributable. A material assertion
  no record covers is **`escaped`** — an unattributed claim per CLAUDE.md
  §10.5 ("*Unattributed claims must be flagged, not asserted*"), the
  fabricates-without-emitting-a-claim threat no predicate can see. The escape
  *basis* is always recorded (`no_lexical_candidates` vs `judged_uncovered` vs
  `escalation_unconfirmed`) so a paraphrase false-escape is legible.
- **Materiality (the bar that keeps the diff usable).** `classify_materiality`
  quotes §10.5 verbatim; the *same* classifier path is calibrated against the
  engine's own 406-entry ledger (`harness/materiality_sets/` — 393 deduped
  auto-labeled positives; 30 **unlabeled** negative candidates a human must
  label, the E1.5 rule). Recall is measurable now; **precision is forced to
  `None` until labeled negatives exist** (positives-only precision would be a
  spurious 1.0). Every completeness report stamps the calibration state in its
  notes.
- **Status calibration (label drift).** `confirmed`-not-grounded =
  **overclaimed** (hard; reuses E2's integrity finding — a supplied E2 result
  costs zero extra confirmed-direction judge calls). `inferred` that clears
  the confirmed bar (E2's own `meets_bar` under the `confirmed` policy) =
  **underclaimed** (soft, advisory — integrity-safe but calibration-wrong).
  Unverifiable claims are surfaced as `unverifiable`, never conflated with
  overclaiming.
- **Batch-failure posture.** Unlike E2 (hundreds of calls), an E3 run makes
  thousands; a per-assertion/per-chunk judge failure is **surfaced as an
  `unjudgeable` finding / `ChunkFailure`** rather than aborting the batch —
  a report with the failure visible serves integrity better than no report.
  Zero-assertion density anomalies and ledger records matched by no assertion
  are also surfaced in the notes.

## E4 — Regression golden-set (`regression.py` + `regression_baselines/`)

The safety net the length-lift work lacked: the current section JSONs are
frozen as golden baselines, and any future artifact — after a drafting
soft-cap lift (D2/D3), a prompt change, or a model swap — is diffed against
them so an integrity/quality regression is surfaced instead of sliding
through. Native on the substrate (no framework — DeepEval's pytest lane earns
in at E5, per the Wave-0 decision gate); two lanes, deterministic-first:

- **Deterministic fingerprint lane (zero judge, offline, committed).**
  `freeze_section_fingerprint` snapshots the claim ledger (matched by
  *meaning* — `(claim_summary, status, source_ref)`, never bare `claim_id`),
  per-sub-section prose hashes + char counts, and a canonical
  formatting-invariant artifact hash. `compare_section` /
  `compare_to_golden_set` classify every drift: a **removed claim, a status
  change, a source_ref swap, a dropped sub-section, a missing section** are
  *breaking* findings; an added claim/section, prose growth,
  prose-changed-while-ledger-unchanged (the escaped-claim risk zone — re-run
  E2/E3 there), and a confirmed-share drop (grounding-density quality signal)
  are advisory context. The frozen goldens live in
  `harness/regression_baselines/` (191 + 119 + 96 claims = the full
  406-entry ledger); loading an empty golden dir **fails closed** (a check
  against no baselines would vacuously pass).
- **Judge lane (E2 reuse, runs when the pinned judge is live).**
  `freeze_section_grounding` / `compare_section_grounding` wrap E2's
  `freeze_baseline` / `compare_to_baseline` — per-claim grounding invariance
  (*form may change, grounding may not*) as the regression assertion after a
  redraft.

**CI wiring — merge-advisory, human-decided, never run-blocking.** The
standing suite (`tests/harness/test_regression_golden.py`, marker
`harness_regression`) diffs the live sections against the committed goldens on
every full pytest run; `python -m harness.regression check` does the same from
the command line (exit 1 = drift, exit 2 = fail-closed). A breaking finding is
*advice to a human*: refreeze (`… freeze`) and commit the golden diff in the
same PR if the change is intentional, investigate if not. `RegressionReport`
enforces `advisory=True, blocking=False` structurally, and nothing in `runner`
reads any of it.

## Pre-evaluation profile (`profile.py` + `profiles/`)

The rubric lane (E5) grades under a **pre-evaluation profile**: one versioned
configuration bundle that names the instrument, the option-tag grammar, the
criterion-to-section mapping, the scorecard file (scale, weights, thresholds)
and the rubric-set file. Every call-specific literal that used to live in
harness Python is a profile field. `harness/profiles/msca_pf_default.json`
reproduces the original defaults; `tests/harness/test_profile.py` pins that
`harness/**/*.py` carries no instrument-name literal outside `profile.py`.

| Piece | Where |
|---|---|
| Profile document (pure configuration) | `harness/profile.py` — `load_profile`, `default_profile`, `parse_scoring`, `profile_version` |
| Bundle loader (profile + substrate + rubric set + scoring) | `harness/rubrics.py` — `load_profile_bundle` → `ProfileBundle` |
| Consumers | `expectations.py` (grammar, instrument type, criterion map), `rubrics.py` (form name in the assessor system prompt), `rubric.py` and `commands/rubric_grading_run.py` (`--profile`) |

**Versioning.** The profile version is a hash over three pins: the profile
document's canonical hash, the scorecard file's canonical hash, and the
rubric-set fingerprint. Any bundled component change moves it. The document
must also carry the scorecard ID + version and the rubric-set ID + version
the loaded files hold (the same bijection rule the rubric set applies to the
scorecard). A mismatch refuses to load. Reports and the E4 rubric baseline
carry `profile_id` and `profile_version`.

**Scorecard exclusions.** A scorecard `excluded_aspects` entry the registry
no longer carries is recorded as absent (`present_in_registry=False`), not
graded, and not an error: the scorecard is still reproduced.

## What the harness does *not* do (through E4)

- It computes only the metrics built so far (E1.5 calibration, E2 status-aware
  faithfulness, E3 ledger completeness + status calibration, E4 regression
  golden-set). E5–E9 (evaluator G-Evals, the α-block assertion, graph-retrieval
  precision/recall, the run-dependent behavioural suites) are later tickets.
- It adopts **no** Ragas / DeepEval / PromptFoo dependency. Their exact metric/API
  names predate the knowledge cutoff and must be confirmed against current docs at
  build time (guardrail: API currency); E2 **and E3** are custom metrics on the
  substrate (the framework question re-opened at E3 — prose decomposition being
  Ragas's headline primitive — and closed native again: the decomposition judge
  is a bounded prompt on the existing substrate and the ledger-diff is custom
  either way), and framework adoption is deferred to the lanes where a primitive
  is irreplaceable (E5/E8/E9). Nothing here imports them.
- It does not auto-gate a merge. E1.5 supplies the *mechanism* to graduate
  advisory → human-gating (`graduation_for`), and every report is
  `blocking=False` by construction; graduation still requires a human-labeled
  gold set and a judge that clears the operator's threshold; the seeded gold set
  ships **unlabeled** (as do E3's materiality negatives), so the harness remains
  advisory until a human labels them and re-runs calibration.
- It does not run the DAG. Every metric through E4 reads frozen artifacts; zero
  DAG runs.
