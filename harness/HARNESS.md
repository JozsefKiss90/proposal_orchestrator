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

**Shipped profiles.** Three, each with its own scorecard and rubric set:

| Profile | Instrument | Scorecard | Rubrics | Expectations |
|---|---|---|---|---|
| `profiles/msca_pf_default.json` | MSCA-PF | `evaluator_scorecard_msca_pf.json` v2.2 | `rubrics_msca_pf.json` | 9, one excluded |
| `profiles/ria_default.json` | RIA | `evaluator_scorecard_ria.json` v4.0 | `rubrics_ria.json` | 6, none excluded |
| `profiles/msca_dn_2026_default.json` | MSCA-DN | `evaluator_scorecard_msca_dn.json` v2.2 | `rubrics_msca_dn.json` | 10, 26 excluded |

`DEFAULT_PROFILE_PATH` still points at the MSCA-PF one; the RIA profile is
selected with `--profile harness/profiles/ria_default.json`.
`tests/harness/test_ria_profile.py` re-reads the RIA aspect texts, criterion
names, scoring levels, scale, thresholds and maximum from the stored
`ef_he-ria-ia_en.pdf` and compares — verbatim up to whitespace collapsing, since
the form breaks every aspect across lines. A drifted scorecard turns the suite
red rather than redefining what is graded.

Two scorecard fields the loader treats as transcribed are Inferred for an RIA,
because the schema fits a multi-variant form better than a single-type one:
`option_tag` (the form annotates no aspect) and `weight_pct` (an RIA is
unweighted). Both are declared in the scorecard's `provenance` and
`scoring.weighting_note`, and recorded as Milestone 1 defects F1 and F2 in
`docs/tier4_orchestration_state/validation_reports/ria-pre-evaluation-profile_2026-10-01.json`.

The MSCA-DN profile is authored, not hand-written. `tools/author_msca_dn_bundle.py`
derives the ten aspect texts, the scoring levels, the weights and every quote from
the stored evaluation form and General Annexes Part 15. It derives the AF V6.0
section headings with the `#@...@#` tags stripped. It replays byte-equal
(`--check`). The form's one untagged Impact bullet is resolved to Doctoral
networks with Inferred status and three grounds in the scorecard's provenance.

The bundle carries two things the other profiles do not. `excluded_sections`
records Part B2 section 11 (RAISE DN), which is no evaluation-form aspect and
belongs to another call. `criterion_appendix_mapping_msca_dn.json` names the
table rows each criterion receives beyond its own section at the criterion-grading
stage. The rubric set pins that file's sha256, so a change to the mapping is a
rubric-set change and never a scoring-time assembly. A profile declares the
mapping under `criterion_appendix_mapping.path`; `load_profile_bundle` loads it
against the rubric set's pin (`appendix_mapping.py`) and refuses a drifted or
unpinned file. Resolution is by candidate sub-section: the import flattened
Table 3.1 a to prose and section 8 carries no rows, so a finer locator would
fail on the rows that matter.

`Scoring` also carries `scale_max` (the top level key), `score_resolution`
(from the scale wording: one decimal place, half-marks, or integers; any other
wording declares none and the step is not checked, which the aggregate records)
and `individual_threshold` when the scorecard states one. The criterion-scoring
stage bounds every assessor score by the first, steps it by the second when
declared, and checks the third. The profile also owns the
baseline's target call (`target_call`), derived from the Tier 2B work-programme
extract, which the ESR intake never carries. `tests/harness/test_msca_dn_profile.py`
re-derives all of it and pins the RIA and MSCA-PF registry entries by hash, since
Phase 1 has destroyed a registry entry before.

The DN candidate is an external PDF, not a Phase-8 output. `tools/import_external_proposal.py`
(spec PE-03) imports it into the workspace graph root `workspaces/msca_dn/` on the
Claude-free substrate `runner/external_proposal.py`: one page source per PDF page,
fifteen sub-sections anchored `1.1` to `3.2` and `4` to `8` in three section artifacts,
tables rendered one pipe-delimited row per paragraph, a claim ledger of rule-selected
sentences frozen `unconfirmed` with a span into their page, and a v2 document record
(`orch.dev_graph.document_snapshot.v2`, which requires a span on every
`source_grounded` claim). The import manifest under `dev_graph/imports/` carries the
extractor, normalisation, table-rendering and claim-extraction versions that PE-05's
preflight binds. `tests/test_msca_dn_import.py` re-derives the import and checks every
sub-section verbatim against the PDF under the declared normalisation.

## Blind assessment (`blind_assessment.py` + `commands/blind_assessment.py`)

The blind pre-evaluation lane assesses one specified candidate against a
pre-evaluation profile with the injectable assessor, without running the
production pipeline. A candidate is a directory of section artifacts, one
`<section_id>.json` per section the profile's criterion-to-section map names.

| Piece | Where |
|---|---|
| Candidate loader, content hash, bound report, writer, loader | `harness/blind_assessment.py` |
| Module command (`assess`, `verify`) | `py -3.10 -m harness.commands.blind_assessment` |
| Reports | `harness/blind_reports/blind_<hash12>_<NNNN>.json` (default `--out-dir`) |
| Provenance | `harness/provenance/blind_assessment.jsonl` |
| Document route (`--document`) | evidence via `runner.dev_graph.build_package` under the `blind_pre_evaluation` view; materialised under `<out-dir>/candidates/<document node id>/` |
| Leakage guard | `assert_no_leakage` → `LeakageError`, before any assessor call |
| ESR intake | `runner.dev_graph.record_esr_intake` / `read_esr_intake`; `--intake <id>` stamps availability |

**Binding.** The report and every cell carry the candidate hash (the
formatting-invariant canonical hash over the parsed section artifacts), the
profile version and the assessor pin (`model@version`). `load_report` and the
`verify` sub-command recompute the candidate hash from disk and reject a
report whose hash differs, naming both hashes. A cell bound to another
candidate cannot be placed in a report.

**Scope.** A candidate missing a required section is assessed over what it
holds; the report is labelled `partial` and lists the missing sections by
criterion and section id. A candidate holding none of the required sections
is refused. `assess` exits `1` on a partial report so the operator sees it.

**Evidence and leakage.** With `--document`, the command builds the dev-graph
snapshot, asks the package builder for the evidence around the document under
the blind pre-evaluation view policy, and then asserts that no included item is
an assessment, finding or change request or carries a historical-feedback tag
(`historical_feedback`, `historical_score`, `target_score`, `repair_plan`). The
policy is the first check; the guard is the second. A violation raises
`LeakageError`: exit `2`, no assessor call, nothing written. The package's
passages and claims are materialised as section artifacts, so the candidate
hash and `verify` work unchanged. An incomplete package is refused. The
`--candidate <dir>` route grades operator-supplied section artifacts with no
package and no guard; its report carries `evidence_source: candidate_directory`
and cannot stamp an intake.

**ESR intake.** ESR availability is intake state (`unknown`, `unavailable`,
`not_applicable`, `available`), recorded once per intake id and never derived:
a prior submission without a declaration stays `unknown`. `--intake` stamps the
availability and intake id on the report. An intake whose permitted purpose is
`esr_informed_review` is refused: that is a separately labelled task, and a
report's `task_label` can only be `blind_pre_evaluation`. Availability never
changes the blind package.

**Assessor.** Each cell is one coverage grade (`grade_expectation`): the
rubric's versioned pack, an N≥3 majority panel, provenance per sample. A
malformed assessor response fails the run through the judge's no-repair rule
and no report is written. Grounding (E5d) is not part of the blind lane: an
evaluator sees the candidate, not the Tier-3 sources behind it.

**Two values per cell.** A cell reports `addressal` (the coverage verdict)
and `grounding` beside it: `in_verdict` when the pack carried claim-ledger
entries, `unassessable` when it carried none. `--no-claims` withholds the
ledger structurally (`include_claims=False` on `build_evidence_pack`): the
ledger file is never opened, no claim is rendered or charged, prose receives
the whole usable budget, and the pack renders a divider saying grounding is
unassessable. The report records `include_claims`. An imported proposal whose
ledger is not trustworthy for grounding is assessed this way; the integrity
audit owns that axis.

**Criterion scores (`criterion_scoring.py`).** A separate stage after the
cells produces the holistic 0–5 score per criterion, because scores are
awarded for criteria and not for aspects (General Annexes Part 15). The scorer
reads the criterion's **complete section verbatim**, never a pack, plus the
sub-sections the profile's criterion appendix mapping declares
(`appendix_mapping.py`, sha256-pinned by the rubric set). Every score names
its complete input by hash (`input_hash`, section and appendix together;
`section_hash`, the section alone) and records the mapping version. An input
with a missing section, an unresolved declared row or more tokens than the
budget is reported incomplete and **not scored**. Nothing is truncated. The
stage has its own budget (`--criterion-budget`, default the uncapped 32768),
because whole sections are the point of the lane. The
cells of the criterion accompany the section as advisory findings and can
never replace it: an input without section text is refused. Five samples per
criterion by default (`--criterion-n`); the median is the score and the spread
is labelled **within-assessor repeatability**, which is all five samples of one
pinned assessor can measure. The total follows the scorecard
(`S = 10E + 6I + 4Q` on the MSCA form, a plain sum on an unweighted one) and
both thresholds, per criterion and overall, are checked and reported. Every
criterion score is bound to the report like a cell; `verify` checks the
binding. `--skip-criterion-scores` runs the cells only. The library default
(`assess_candidate(criterion_samples=None)`) skips the stage; the command runs
it.

**Immutability.** The writer never overwrites: a rerun writes the next
sequence number for the same candidate hash and earlier reports stay
byte-identical. `BlindAssessmentReport` enforces `advisory=True,
blocking=False` at construction and on load.

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
