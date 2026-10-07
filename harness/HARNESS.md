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

The register has two halves and two owners. The derived half is measured from the
PDF by the importer; the declared half is the operator's per-sub-section statement
of `presence` and `transformation`, and both tools render the whole file on every
run. So the declared half has a durable input of its own, one file per revision,
`docs/tier3_project_instantiation/source_materials/msca_dn/declarations/<revision_id>.json`
(`tools/fidelity_declarations.py`, R01). The tools read it, carry its rows into the
register unchanged, order them by the derived inventory, and never write it. A
declaration therefore survives every later authoring run and both `--check`
commands pass straight after one. No input means no declarations and the register
keeps the empty declared half it has today, byte for byte, so the comparison
artifacts that recorded its hash stay replayable. A malformed input is refused
before anything is written. So is a declaration the register holds and the input
does not, unless the register records older input bytes than the input now has — the
operator withdrew that row by editing the input, and the input is the newer
statement. The declarations directory holds a README with the format.

Both inputs are absent today, so both declared halves are empty. R04 drafted what
each could say: `tools/draft_fidelity_declarations.py` transforms the registers,
the import manifests, the dispositions and the active review notes into one draft
per revision under `docs/tier4_orchestration_state/msca_dn/declarations/`, plus a
review checklist. Each draft covers its revision's whole derived inventory and
carries the adoptable input verbatim under `declaration_input`. It keeps three
claims apart, because each is checkable somewhere else:

- extraction fidelity against the sanitised PDF — Confirmed, from the derived half;
- the difference between the sanitised revisions — Confirmed, from the manifest's
  page-by-page comparison;
- fidelity against the submitted original — Unresolved on every row, until PE-09.

Each draft also enumerates what adoption would cost — the artifacts that
pin that register's bytes — and which dispositions lean on which sub-section's
declaration. The renderer never writes into Tier 3, and no row claims operator
authorship.

## Blind assessment (`blind_assessment.py` + `commands/blind_assessment.py`)

The blind pre-evaluation lane assesses one specified candidate against a
pre-evaluation profile with the injectable assessor, without running the
production pipeline. A candidate is a directory of section artifacts, one
`<section_id>.json` per section the profile's criterion-to-section map names.

| Piece | Where |
|---|---|
| Candidate loader, content hash, bound report, writer, loader | `harness/blind_assessment.py` |
| Module command (`preflight`, `assess`, `verify`, `freeze`, `audit`, `compare`, `review`) | `py -3.10 -m harness.commands.blind_assessment` |
| Frozen baseline: conditions, byte copy, freeze record, hash-checked loader | `harness/blind_baseline.py`; `--baseline-dir <dir>/blind_baseline_<sha12>.json` + `.freeze.json` |
| Integrity audit: five consistency checks over parsed rows, grounding axis Unresolved, baseline binding | `harness/integrity_audit.py`; reports `<out-dir>/integrity_<hash12>_<NNNN>.json` |
| ESR comparison: one row per historical observation, declared dispositions resolved against the frozen baseline, scores compared apart | `harness/esr_comparison.py`; `<out-dir>/comparison_<sha12>_<NNNN>.json` + `revisions_<sha12>_<NNNN>.json` |
| Operator review: a written comparison rendered for a human, every reference re-resolved, counts recomputed, agreement declared | `harness/operator_review.py`; `<out-dir>/operator_review_<sha12>_<NNNN>.md` + `operator_decisions_<sha12>_<NNNN>.md` |
| Evidence preflight: realised pack set, pack-set hash, seven-section report | `harness/evidence_preflight.py`; reports `harness/blind_reports/preflight_<hash12>_<NNNN>.json` |
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

**Evidence preflight (`evidence_preflight.py`).** A Claude-free command run
before any quota is spent:

    py -3.10 -m harness.commands.blind_assessment preflight --document <id> --graph-root <repo> [...]

It takes the same evidence-selecting flags as `assess` (`--budget`,
`--span-fraction`, `--no-claims`, `--criterion-budget`, `--transport`,
`--package-budget`, `--import-manifest`), realises every pack and criterion
input exactly as `assess` would, and writes
`preflight_<hash12>_<NNNN>.json` beside the blind reports (never overwritten).
The report carries seven things:

1. The anchors present, against the rubrics the profile declares. A missing
   anchor is reported, not raised.
2. The `not_relevant` exclusions per expectation, with their token cost. No
   other artifact shows them, because that exclusion never flips a pack to
   `insufficient_context`.
3. The `over_budget` exclusions and the pack status they produced.
4. The table rendering and row-parse counts over the candidate's pipe-delimited
   rows, against the import manifest when one exists.
5. The package completeness under the package budget.
6. The leakage scan: the package guard, the snapshot's input list against every
   `esr` directory on disk (the historical evaluation is never snapshotted), and
   the instance-one word scan over the graph root.
7. The pins.

Exit `0` with no flag, `1` with flags to read, `2` when it could not run.

**Pack-set hash.** The pins are the candidate hash, profile version, rubric set,
scorecard, appendix mapping, policy, snapshot and package, **and** every input
that selects evidence. The three budgets arrive as flags and are covered by no
other pin; the demo recorded a case (F9, 2026-10-02) where a provider's
rate-limit ceiling fixed the pack budget and so predetermined every grade. The
binding is therefore the **pack-set hash**: a canonical hash over each realised
pack's selection record (without its machine path) plus the exact text it
renders for the assessor, each criterion input's hash, and the parameter values
themselves. A change to any selection input moves it, whether or not it changed
the selected text, and whether or not anyone listed that input. The parameter
values are also recorded beside the hash, because a bare mismatch does not say
what moved. The hash is a hash of an
output and is not provenance: two extractor versions producing byte-identical
packs are indistinguishable by it, so the import manifest, which carries the
extraction, normalisation and table-rendering versions, is pinned separately by
its sha256.

**`assess` requires it.** `assess --preflight <file>` loads the report,
re-derives the pack set under its own flags, and refuses (exit 2, before the
assessor is constructed, nothing written) when the candidate hash, the profile,
any parameter, the snapshot, package or policy, the manifest pin or any pack
moved, naming every field that did.
On a match the blind report carries `preflight_pack_set_hash` and
`preflight_report`. The library function `assess_candidate` takes the hash as an
optional stamp and does not check it; the command does.

**Immutability.** The writer never overwrites: a rerun writes the next
sequence number for the same candidate hash and earlier reports stay
byte-identical. `BlindAssessmentReport` enforces `advisory=True,
blocking=False` at construction and on load.

**Frozen baseline (`blind_baseline.py`, spec PE-06).** A written report becomes
*the* baseline through

    py -3.10 -m harness.commands.blind_assessment freeze --report <file> --candidate <dir> --baseline-dir <dir>

The command re-binds the report to the candidate, then checks the baseline
conditions by name (`BASELINE_CHECKS`). The conditions are:

- dev-graph evidence: snapshot id, package id and policy version present;
- the preflight pack-set hash and report present, the preflight file readable,
  and its `pack_set_hash` equal to the report's;
- candidate hash, profile version and assessor pin present;
- an `assessor_transport` that the version tag names;
- complete scope;
- every cell with an N>=3 panel and an agreement value;
- a median and a spread for every criterion, from a panel of at least five,
  and a determined total.

Any failing condition is named and nothing is written (exit 2). On success the
report is copied byte for byte to `<baseline-dir>/blind_baseline_<sha12>.json`.
A `harness.blind_baseline_freeze` record is written beside it. The record
carries every binding, the per-cell `n`, agreement and score spread, the
per-criterion score and spread, the total, and the report's own spread label
(within-assessor repeatability). `checks_passed` is derived from the check
list, never declared. A baseline directory holds one freeze; a second is
refused. Later stages read it through `load_frozen_baseline`, which re-hashes
the copy and refuses an edited one. The report carries `assessor_transport`
(the command's `--transport` choice) and `assessor_invocation` (the backend's
own account of what its child could reach), so both conditions are structural.

**The bound bytes are protected from line-ending translation.** Every
binding above is a sha256 of file bytes: the frozen copy, the preflight
report, the import manifest the preflight pins, the ESR record and the
dispositions, the rubric set's pin on the criterion appendix mapping, and the
byte-equal `--check` of the two authoring tools. Under `core.autocrlf=true` a
fresh checkout rewrote all of them LF to CRLF and seven of eight bindings
failed (measured 2026-10-07 on a worktree of `67a3174`; decision log
`msca-dn-line-ending-bindings_2026-10-07`). The repository's `.gitattributes`
marks those trees `-text`, so git stores and checks out their bytes
unchanged; the scope is only the hashed trees, nothing is renormalised, and
no recorded hash was regenerated. A new byte-bound artifact outside those
trees needs a rule there before it is committed.

**Blindness is tested, not asserted.** Three controls, each with a test that
would fail if it broke:

1. The subscription backend passes the transport the **explicit empty tool
   list** (`runner.claude_transport.NO_TOOLS`), never `None`. `tools=None`
   omits `--tools` and leaves the CLI's built-in tools live: measured
   2026-10-04, a no-flag assessor asked to read `./CLAUDE.md` did so. The
   transport renders the empty list as `--tools "" --strict-mcp-config`,
   because `--tools ""` alone still exposes the operator's MCP servers
   (measured 2026-10-05: a filesystem reader was listed; with
   `--strict-mcp-config` the tool list was empty).
2. The child runs in a fresh empty **working directory outside the
   repository** (`assessor_working_dir`); one inside is refused.
3. The argv is pinned at the level handed to the operating system, not at the
   Python keyword (`tests/harness/test_subscription_judge.py::TestBlindnessAtTheArgvLevel`,
   with `Popen` replaced). A **planted-marker test**
   (`tests/harness/test_blind_baseline.py::TestPlantedMarkers`) writes a unique
   string into the historical evaluation and into a Tier 5 draft. It shows the
   string reaches no rendered prompt, the materialised candidate or the report.
   A non-vacuity check shows the candidate text does reach the prompts.

The subscription builder also refuses a `HARNESS_JUDGE_VERSION` that does not
contain `claude-cli`, so a report from that transport cannot carry another
transport's tag.

**Integrity audit (`integrity_audit.py`, spec PE-07).** A Claude-free,
deterministic audit of one candidate, run after the baseline is frozen:

    py -3.10 -m harness.commands.blind_assessment audit --document <id> --graph-root <repo> [--baseline-dir <dir>]

It reads the same materialised section artifacts the blind lane reads, parses
the rendered pipe-delimited rows (a repeated header at a page break re-opens
the same table; a row that opens no new entry is merged into the previous one)
and the label-value work-package headers, and runs five checks in spec order:
work-package block fields and DCs involved against the DC projects of 1.1;
each deliverable's package and window; each milestone against the
deliverables it names (naming none is reported as *undeclared*, with the
related packages' deliverable months as context, never as a failure); the DC
table against the 1.1 projects (the recruiting participant against the host
line is *not comparable* after sanitisation and is reported as such); the
risk table against mitigations named in prose, and whether any row states a
threshold. Every finding has a `kind` from a closed set (`inconsistency`,
`missing_field`, `unparsed_cell`, `undeclared_dependency`, `out_of_window`,
`not_comparable`, `unlinked_prose`), a subject, the paragraphs it cites, and
the row text. **No finding is a score**; a test pins that no score-shaped key
appears in a report, and findings never move the exit code.

**What a check compares, and what it only notes (ticket R03).** Two of those
comparisons put unlike things side by side and were corrected. *DCs involved*
is now compared in one direction only: a package is reported when a DC project
in 1.1 names a package that package's own DC set omits. The reverse is not
reported, because a host line states the packages one candidate's research
sits in, not every package that candidate works in — which is why every
training, dissemination and management package involves the whole cohort and
appears on no host line. *An appointment period* is compared with a
work-package window for overlap only: a candidate has to be employed while the
package they contribute to runs. An appointment that outlasts every package is
a check note with its months, not a finding, because the recruitment table's
own duration column is the only bound the candidate states and no source ties
that period to a package window. A third note says what the milestone check
rests on: a dependency is not a column of the milestones table, so an
`undeclared_dependency` finding records an absence rather than a declared
value the candidate contradicts. No `kind` changed, so every reference an
earlier report recorded still resolves.

**The work-package header (`split_header_fields`).** A header field is
`<label> <value>`, and the labels are looked for in the order the application
form fixes them: `WP Number`, `WP title`, `Start month - End month` (or a
standalone `Start month` and `End month`), `Lead participant`, `Participants`,
`DCs involved`, `Objectives`. Each label is searched for only after the label
before it, so a value that happens to carry a later label's word cannot be read
as that label, and a paragraph is a header only if it *opens* with a label. One
rule therefore reads both layouts the extraction produces: a paragraph per
label, and every label of a header run into one paragraph, which is what page 45
of the revised MSCA-DN candidate carries. A collapsed header parses to the same
fields and keeps its one paragraph as the block's location, so every finding
over it still cites a real paragraph and quotes the candidate's text.
`collapsed_header_labels` on the parsed block records which labels arrived that
way, matching the import register's `headers_collapsed_into_one_block`. The
header precedes the task list: once a block's tasks have begun, a paragraph that
merely opens with a label word is body prose, may fill a field the header left
unset, and never replaces one. An unreadable timing value, a `WP Number` value
carrying more than a number, and a field declared twice with two different
values are each reported as an `unparsed_cell` finding quoting the header, never
guessed.

**Ligatures (`fold_ligatures`, `Folded`).** A PDF may carry `fi` as one code
point, so a search for the unligatured spelling misses it. Every comparison and
search in the module runs over the folded form: the table-heading normaliser,
the content-word tokeniser the risk check links prose by, the header labels and
the DC-project patterns. Nothing in a report quotes the folded form. `Folded`
maps a match back through an offset map and every value is cut out of the
candidate's own text, so a ligature changes what matches and never what a
finding says. Original text, source offsets, assertion locations and candidate
hashes are untouched.

The grounding axis enumerates the ledger (`validation_status.claim_statuses`)
and reports every claim `Unresolved` with the reason *supporting sources
removed by sanitisation* (spec decision 15). No judge runs. A vacuous ledger
is flagged; a ledger entry declaring a status other than `unresolved` is
flagged with its declaration visible and still reported Unresolved. The
ledger's `source_ref` is the claim's own verified span into the proposal's
page sources, carried as `assertion_location`, never treated as a source.

The audit writes only its report, and the command rebuilds the snapshot after
the write to show the id did not move. With `--baseline-dir` it loads the
freeze through `load_frozen_baseline` and states one of: `bound` (candidate
hash and snapshot id equal), `re-derived` (same candidate, moved snapshot id;
flagged), `candidate_differs`, or `snapshot_unknown` (directory route). Without
it the report says no baseline was consulted. Exit `1` on any flag, `2` when
the audit could not run (a baseline directory with no readable freeze included).

**ESR comparison (`esr_comparison.py`, spec PE-08).** A Claude-free comparison
of the frozen blind baseline with the historical Evaluation Summary Report:

    py -3.10 -m harness.commands.blind_assessment compare --baseline-dir <dir> --esr <esr.json>
        --dispositions <dispositions.json> --candidate <dir> --register <fidelity_register.json>
        [--historical-candidate <dir>] [--audit <integrity_*.json> ...] --out-dir <dir>

(one command line; wrapped here for width)

Two inputs are operator-authored. The **ESR record** transcribes the report
one observation per labelled point. The text is verbatim and the severity is
the ESR's own sentence (spec decision 13); strengths are recorded too. The
**dispositions** are the declared half. They bind to one baseline by the
report copy's sha256 and to one ESR record by its sha256. Each row names a
disposition from the closed set, the blind and audit findings it rests on,
the candidate passages it quotes, the register entries it relies on, an
explanation, and a proposed revision.

The command turns declarations into traceable rows by resolving every
reference. A blind reference (`criterion_shortcoming`, `criterion_strength`,
`cell`, `cell_member`) is quoted from the frozen report copy. An audit
reference (`report`, `check`, `index`) is quoted from an audit given on the
command line, which must be over a candidate in play. A quote must occur in
the named sub-section's text, ligatures folded and whitespace collapsed. A
register pointer (`derived/figures/images_on_any_page`, `/`-separated because
sub-section ids carry dots) is resolved to its value. When a historical copy
is given and a row declares no historical quote, its current quotes are
re-verified against that copy and stand for it where they occur. One
unresolved reference refuses the comparison and nothing is written.

The dispositions are the ticket's five, each with the basis it must carry:

| Disposition | Needs |
|---|---|
| `independently_detected` | a blind or audit finding; the row records `detected_by` lane(s) |
| `partially_observable` | a finding and a register entry naming what the copy preserves only in part |
| `not_assessable_from_this_copy` | a register entry naming what sanitisation removed |
| `not_detected_despite_sufficient_preserved_evidence` | the preserved passage quoted and verified, no finding, a declared `evidence_preserved_status` |
| `addressed` | a verified quote from the historical copy and one from the current copy; never for a strength |

The summary counts every disposition and states `assessable` and the
`assessable_fraction`. Detection is rated only over shortcomings that are
neither `addressed` nor `not_assessable`, as two figures: `rate_detected`
counts only `independently_detected`, and `rate_detected_or_partial` adds the
partial rows, whose evidence this copy only partly carries. `not_assessable`
is counted separately, never as a failure, never dropped. A blind shortcoming cited on
an ESR strength marks the row `contests_historical_strength`. Criterion
scores are compared in a separate `score_comparison` block (historical score,
blind median, spread, difference, total) that states no deduction is
attributed to any individual criticism and that the difference is not
interpretable as model error. The revisions go to a second artifact in a
derived order (severity, criterion weight, disposition, ESR order), with
`addressed` rows listed as closed; an open shortcoming without a proposed
revision is a flag (exit `1`). Nothing is overwritten: both artifacts take
the next sequence number for the baseline's hash.

On the MSCA-DN case the committed ESR record carries 29 observations: 15
shortcomings (8 in the two 'shortcoming' clusters, 7 minor) and 14 strengths.
Of the 14 rated shortcomings the blind or audit lane detected 6 and partly
observed 2; 6 were not detected on preserved text and 1 is not assessable
from this copy. Of the 14 strengths, 9 are matched by blind strengths and 5
are partly observable, with 8 carrying a blind shortcoming on the praised
point. No row is `addressed`. The dispositions are declarations for operator
review; `tests/harness/test_esr_comparison.py` re-resolves them against the
committed artifacts.

**Operator review (`operator_review.py`, ticket R02).** The comparison is a
JSON artifact bound by hashes; the operator has to read it. This renders it:

    py -3.10 -m harness.commands.blind_assessment review --comparison <comparison_*.json>
        --notes <review_notes_*.json> --out-dir <dir>

Every other input is read from the comparison, not from the command line. A
report that could be rendered against a different ESR record or candidate
than the comparison used would be a new interpretation wearing the
comparison's bindings. Each named input is re-hashed on disk — ESR record,
dispositions, register, every audit, the frozen report copy, the candidate's
content hash — and a mismatch refuses the review.

The **review notes** are the declared half, one row per observation, drafted
by an agent and labelled so: `review_state` has exactly one permitted value,
`agent_drafted_pending_operator_review`. Like every record here the notes
carry `advisory: true` and `blocking: false`, and a notes file without them,
or of a schema version this module does not read, is refused. A row declares whether the resolved
evidence supports the proposition the ESR states (`semantic_agreement`:
agreed, disputed, unresolved, not_applicable), the basis for that judgment
and its §12.2 status, what the ESR complains of (`esr_complaint`: an absent
detail, an inadequately explained one, both, other), the uncertainty, a
recommendation (retain, revisit in R03, adjudicated, revisit after the R04
declaration, revisit after the private network) and a recommended disposition.
A row that is not "agreed, retain" must name an `operator_decision`: a disputed
row without a question hands the operator a disagreement and nothing to decide.
A recommended disposition that differs from the comparison's needs one too, and
so does an `adjudicated` row — an adjudication is a reading, never an approval.

A notes file may also name an `adjudication_record` and a
`supersession_note`. The record is re-hashed and listed among the report's
inputs, and the report refuses to cite reasoning it cannot hash. The note is
printed above the counts, so a second rendering of one comparison explains
itself instead of leaving a reader to diff two reports.

Measured on every run and refused on failure: every observation of the ESR
record covered exactly once, every reference resolved again through the
comparison's own resolvers **and** to the text the comparison recorded, and
every count recomputed from the rows and cross-checked against the
comparison's summary. Resolution is a measurement and agreement is a
declaration; they are separate fields, because a finding can resolve
perfectly against the baseline and still be about something else. That is
what R03 adjudicates, and this report is where such a row is named.

Counts keep criticisms apart from strengths. On the MSCA-DN case the
comparison's 15 `independently_detected` rows are 9 strengths the blind lane
praised as the evaluators did and 6 criticisms it caught; the report states
that split before any rate. Two artifacts are written, sharing a sequence
number and overwriting nothing: the full review and a decisions file holding
only the questions. Markdown, LF, under the `-text` tree, so a committed
report replays byte for byte apart from its `Generated:` line. Each committed
report names the notes record it was rendered from, and a test rebuilds each
from that record rather than from file order, so a second rendering never
makes the first unreproducible.

**Semantic adjudication (ticket R03).** A reference that resolves perfectly
can still be about a different proposition, and no code settles that. The
adjudication record (`esr_semantic_adjudications`) is where a reader does,
one row per dispute: what the rule compared and whether the two are the same
relation, a *measured* half and an *interpretation* half with a §12.2 status
each, the consequence, and the decision left for the operator. Evidence is
quoted by reference — candidate quote, blind finding, audit finding, register
pointer, application-form column — and
`tests/harness/test_semantic_adjudications.py` resolves every one of them
through the comparison's own resolvers, re-hashes every named input, and
refuses a record whose evidence does not hold. Classifications are the five
the ticket names plus `unsupported_lane_claim`, for an assessor statement the
input that assessor received contradicts; it is neither an extraction issue
nor a sanitisation limitation, because nothing was mis-read and nothing was
removed. A `failure_mode` separates a point no lane output engages with from a
passage a lane read and rated adequate, read and misattributed, or read and
asked a different question of. The distinction is recorded, never counted: no
rate in any artifact uses it.

## Response checkpoint and the bounded re-ask (`response_cache.py`)

An assess run is 45 assessor calls on the shipped profile and writes nothing
until the last one is graded. On 2026-10-06 call 44 came back as sound JSON
ending `..."rationale": "...", }` — one trailing comma — and the fail-closed
parse discarded 43 paid-for calls with it. Two changes, neither of which
loosens a parser.

**Every raw response is checkpointed as it arrives.** `Judge.raw_invoke` is the
single seam every assessor call passes through, so the cache lives there. The
file is JSONL under `.harness/checkpoints/` (never `--out-dir`: a failed run
still writes no report), one header record carrying the run's binding and one
record per response. `--resume <file>` replays those bytes through the same
parsers, provenance builders and verdict arithmetic, then goes live from the
first call the file does not cover, appending to it. `--no-checkpoint` writes
none.

A replay is the response the assessor actually gave, not a fresh draw, and the
report says which it had: `replayed_calls`, `live_calls` and `checkpoint_path`,
rendered as `[NOT a fresh draw]` whenever anything was replayed.

Refusals, all fail-closed: an existing checkpoint is never appended to without
`--resume`; a checkpoint names the candidate hash, profile version, assessor
pin, preflight pack-set hash, `include_claims` and both sample counts, and
resuming into a binding that moved is refused with every moved field named; an
edited response (sha256 mismatch) is refused, not read.

**A response the parsers rejected is kept and never replayed.** The cache sits
below the parsers and cannot tell a usable response from an unusable one, so
`Judge.evaluate` and `criterion_scoring._draw_sample` tell it: a discard marker
is appended beside the record. The bytes stay in the file as the faithful
record of what the assessor said; a resume skips them and redraws that call.
Without this, the response that killed a run would kill every resume of it.

**A malformed criterion sample is drawn again**, up to
`MAX_SAMPLE_REDRAWS` (two extra draws, three in all), over the identical
prompt. Re-asking is not repairing: nothing from a discarded draw is patched,
merged or partly read, and every one is recorded on the score as a
`DiscardedDraw` — index, attempt, the parser's own message, sha256 and length.
An assessor that cannot produce the schema three times running is not having an
accident, and the run fails closed carrying the parser's message. The criterion
system prompt now also asks for strict JSON in as many words, which moved the
criterion `prompt_hash`.

**Salvage (`salvage`).** One-off recovery for a run that spent its quota before
the checkpoint existed. The `claude` CLI writes one session transcript per
assessor call under `~/.claude/projects/<slugified working directory>/`, and the
assessor child runs one session per call in a fresh temp directory, so that
directory is a complete record of the run. `salvage` rebuilds every cell prompt
from this profile and this candidate and matches each transcript on the recorded
user prompt, which must equal the rebuilt one byte for byte. The one allowance is
line endings: the prompt reached the child through a pipe that translated them,
and that single deterministic transformation is undone before comparing.

The binding is computed by the same `_cache_binding` the assess run uses, so a
salvaged checkpoint either resumes or is refused, never half-matches. A
transcript matching nothing is named and left out, which costs the resumed run
one live call and can never cost it a wrong answer. A recorded response that
will not parse is written and immediately marked discarded, so it is redrawn.

Only the cells are recovered. A criterion prompt carries the drawing run's
aspect findings, so it cannot be rebuilt from the candidate alone, and the
criterion system prompt changed when the strict-JSON instruction was added —
replaying a response drawn before that would let a report claim a score from a
prompt that never produced it.

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
