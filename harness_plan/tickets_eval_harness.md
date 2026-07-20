# Tickets: Evaluation & Integrity Harness — out-of-band QA track

Source strategy: `EVALUATION_HARNESS_STRATEGY.md` (v1, 2026-07-20). Reviewed in `EVAL_HARNESS_TICKETS_REVIEW.md` (2026-07-20). **Rev 2** applied that review (E1–E3 lead as M3's verifier; **E1.5** judge-reliability; `ticket 10 → M2-T10`; E7 split; E3 materiality). **Rev 3 (2026-07-20)** corrects two items on code verification:

- **E7a mechanism.** `--dry-run` does **not** evaluate gates (`runner/__main__.py:345` — *"Dry-run does NOT evaluate any gates"*); it prints ready nodes and exits. The α Phase-7 block is the deterministic **`gate_09_budget_consistency`** exit gate (node `n07`) on the MSCA unit-cost derivation — assert it by calling the gate evaluator directly on α fixtures (zero run, no judge). E7a rewritten.
- **E9 unblocked + offline.** The M2 **section-node authoring is done** — vault folders `11…19` are authored incl. the **12 `proposal_section` nodes** (verified 2026-07-20). Graph retrieval runs through the compiler `--from-graph` **Step-0 pass, not a DAG run**. E9 moves out of the run-dependent bucket into the offline track.

This is a **separate, out-of-band QA/CI track** — architecturally distinct from the runtime DAG and the milestone-2 authoring track. It sits alongside M3, not inside M2.

**Scope decision (operator steer): earn-its-lane phasing.** Prove the two headline integrity signals in one framework first; adopt a second/third framework only when its *distinct* lane demonstrates ROI; keep the right to consolidate. Integrity-weighted over quality.

## Referenced dependencies (pinned)

Pin every gating name so no ticket is gated on an undefined artifact (same fail-closed-on-dangling-links discipline `vault_reader.dangling_links()` applies to wikilinks).

- **`M2-T10`** = milestone-2 ticket 10 — the *graph-becomes-authoritative-Tier-3-source* cutover (open-Q #4, `tickets_milestone2.md`). Gates only the run-dependent **E7b/E8** (they reuse the showcase's runs). The offline tickets do **not** wait on it.
- **M2 section-node authoring — ✅ DONE (verified 2026-07-20).** The milestone-2 ticket that authors `proposal_section` nodes has authored vault folders `11_objectives … 19_proposal_sections`, including the **12 `proposal_section` nodes** (PS-excellence-1/1.1–1.4, PS-impact-2/2.1–2.3, PS-implementation-3/3.1–3.2). E9's authoring blocker is **cleared**. (The `GRAPH_SUBSTRATE.md` "walking-skeleton / folders 11–18 unauthored" note is stale — supersede it.)
- **"the showcase"** = the planned flagship end-to-end run (M2 graph-sourced Tier 3 + M3 composition + Opus-for-impact Impact authoring) that produces an evaluator-ready Part B, whose runs **E7b/E8** batch behind. ⟐ **not yet pinned to a canonical ticket — pin before Wave 4 starts** (grep-confirmed it appears in no repo doc as of 2026-07-20; do not treat as defined until pinned).
- **"Opus-for-impact"** = authoring/composing the Impact section with the Opus model (the model choice E6's cost matrix is meant to evidence). ⟐ **pin to its scope line / ticket.**

## Non-negotiable guardrails (span every ticket)

- **Never a fail-closed runtime gate.** No eval metric wires into the runtime DAG. The 138 predicates + byte-equal CI checks remain the only blocking runtime gates (§17 byte-equal replay + fail-closed preserved). The harness gates *decisions about the pipeline* — merges, prompt changes, model swaps, release cuts — in CI, and even there it is **advisory to a human**, not auto-blocking, until judge reliability is characterized (**E1.5**).
- **Deterministic-first routing.** Where a predicate/gate can check a property, it is authoritative; a judge runs only where no deterministic check exists; a green judge never overrides a red predicate. *(E7a is a case in point — the α-block is a deterministic gate, so it is asserted deterministically, no judge.)*
- **Grader–generator independence.** Judge with a non-drafter model over the OpenAI-compatible transport.
- **Judge output is `Inferred`, never `Confirmed`.** Pin judge model+version, temp 0, N≥3 majority where a score informs a decision; log `{judge_model, judge_version, prompt_hash, score, rationale}` as provenance (same discipline as the decision log).
- **Earn-its-lane.** Each framework must prove its distinct lane before the next is adopted. If a lane is better served by a framework already in use, do not add the second tool. (Expect convergence on ~three tools in *distinct* lanes — see the Wave-0 decision gate.)
- **API currency.** Exact Ragas/DeepEval/PromptFoo metric/API names predate the May-2025 cutoff — confirm against current docs at build time before writing any binding (Inferred until then).

## Sequencing — the "avoid extra runs" split

The harness judges **artifacts, not runs** — almost all of it never triggers a DAG run.

- **Offline tickets (E1–E6, E7a, E9)** read frozen artifacts, exercise the deterministic gate evaluator, or run the Step-0 graph compiler. **Zero DAG runs.** E1–E3 lead now (M3's verifier); E7a is a deterministic `gate_09` assertion; **E9's graph data is authored and reached via the `--from-graph` compiler pass, not a run.**
- **Run-dependent tickets (E7b, E8)** observe β→B1 / hostile-input behaviour that needs full pipeline runs. **Gated behind M2-T10 / the showcase:** batch their runs behind the showcase and reuse its artifacts — never ad-hoc. This is where "avoid running phases more than necessary" is enforced.

**Why E1–E3 lead (review MF-1 — the M3 collision).** M3 introduces a **Claude-driven composition pass** that rewrites each section's `content` (de-identify + weave to evaluator-ready prose) while carrying `claim_statuses`/`source_ref` forward **verbatim**. Its anti-fabrication guarantee is *not* determinism (the composer is synthesis — `MILESTONE3_SCOPE.md` §7 calls it a sanctioned "shadow author") but the structural contradiction-detector gates + `no_unsupported_tier5_claims` — the latter itself a **semantic/in-run** gate (absent from the deterministic predicate registry), i.e. the same-model-family judge the strategy §2 says must not be trusted alone. Those gates catch a *wrong* token, not a composer that keeps every canonical token but subtly **weakens the grounding** of a `confirmed` claim. **E2 status-aware faithfulness is exactly that missing check.** So E1–E3 are built **before** M3 composition and reused as the exit check on **M3-T3 / M3-T7** — the independent, out-of-band net M3's §7 risk calls for. *Baseline nuance:* baseline Excellence + Implementation immediately; baseline Impact **after** the Opus-for-impact authoring (the one section that genuinely changes), so you are not diffing against a to-be-discarded version.

## Waves

- **Wave 0 (offline, now — M3's verifier; prove the core in one framework):** E1, E1.5, E2, E3 → decision gate
- **Wave 1 (offline, add pytest/CI lane if it earns):** E4, E5
- **Wave 2 (offline, add prompt-boundary lane if it earns; + the deterministic α-block check):** E6, E7a
- **Wave 3 (offline, graph-retrieval lane — where Ragas earns in; data ready today):** E9
- **Wave 4 (run-dependent, ⚠ behind M2-T10 / the showcase):** E7b, E8

Only Wave 4 needs a pipeline run.

---

## E1. Harness substrate + independent judge config
**What to build:** the out-of-band scaffolding every metric stands on.
**Blocked by:** none (offline).
- [ ] A pinned non-drafter judge over the OpenAI-compatible transport (temp 0; model+version pinned).
- [ ] Provenance logging `{judge_model, judge_version, prompt_hash, score, rationale}` for every verdict.
- [ ] A deterministic-first routing helper: a property with a predicate/gate is never judged; the judge runs only in the semantic gap.
- [ ] Reporting-only output (no CI gate yet); a documented "never a runtime gate / advisory-to-human" boundary.
- [ ] Judge output typed `Inferred`; N≥3 majority scaffold where a score will inform a decision.

## E1.5 Judge-reliability calibration — the "advisory → gating" mechanism
**What to build:** the meta-eval that characterizes judge reliability, so a metric can graduate from advisory to merge-gating and the `Inferred` scores carry a calibration basis. Without it, the guardrail's "advisory until judge reliability is characterized" clause has no mechanism and the harness is permanently advisory by default.
**Blocked by:** E1.
- [ ] A small **human-labeled** gold set (~20–30 `(claim, source_ref, supported?)` pairs) drawn from the real `claim_statuses`.
- [ ] Measure the judge's false-positive / false-negative rate (precision/recall) on faithfulness verdicts vs the gold set; record `{judge_model, judge_version, precision, recall}` as provenance.
- [ ] Define the graduation threshold: until the judge clears it, every metric stays **CI-advisory (human-decided)** — no auto-gating.
- [ ] Re-run on any judge model/version repin (a repin re-opens the advisory-only state).

## E2. Status-aware faithfulness — headline signal #1 [one framework]
**What to build:** faithfulness partitioned by claim status — the "gap masked as confirmed" detector; **also reused as M3-composition's exit check.**
**Blocked by:** E1. Candidate framework: Ragas (native claim-decomposition) **or** a DeepEval custom metric — pick ONE (see decision-gate cascade).
- [ ] Claims partitioned by `status`; `confirmed` → faithfulness ≈1.0 vs its `source_ref` (a `confirmed` claim unsupported by its own source is a hard integrity finding — the threat no predicate can see).
- [ ] `assumed` → judged vs the `working_assumptions.json` declared value, not the source (complements W1: existence → content).
- [ ] `inferred` → faithful as framing/synthesis, softer threshold.
- [ ] Built against the current `excellence/impact/implementation_section.json`; re-points at M2-T10's graph-sourced artifacts unchanged. Reporting-only; zero DAG runs.
- [ ] **M3 reuse:** freeze a per-claim faithfulness baseline on pre-composition prose; re-run on M3-composed output and require per-claim invariance (form may change, grounding may not).

## E3. Claim-ledger completeness + status calibration — headline signal #2
**What to build:** the "escaped claim" detector + calibration drift.
**Blocked by:** E1 (shares E2's framework).
- [ ] Prose decomposed into atomic assertions, diffed against logged `claim_id`s; a non-empty "unledgered assertion" set is a hard finding ("fabricates without emitting a claim" — the threat W1 cannot reach).
- [ ] **Materiality threshold (else self-defeating):** only assertions meeting the constitution's *material claim* bar (the same materiality `no_unresolved_material_claims` / §10.5 rely on) must map to a `claim_id`; non-material prose (transitions, framing, method description) is excluded — without this the "escaped claim" set floods with false positives and the check gets ignored.
- [ ] Claim-status calibration: a `confirmed` that isn't grounded, or an `inferred` fully source-backed (mislabelled down), flagged as drift.
- [ ] Runs on the real section as a ready-made calibration set; reporting-only; zero runs.

### ⟐ Earn-its-lane decision gate (after Wave 0)
Did status-aware faithfulness + ledger completeness surface real issues (or give real confidence) on the current artifacts? Record the finding in the decision log. Only if yes — and only for a *distinct* capability — adopt a second framework in Wave 1. If the chosen framework underdelivered, reconsider it before adding tools.

**Framework-choice cascade (pick consciously at E2).** The Wave-0 pick propagates: **DeepEval** at Wave 0 consolidates E2–E5 **and** E8 (DeepTeam) in one ecosystem (pytest-native; G-Eval / DAG-metric are DeepEval primitives), leaving Ragas to earn in only at **E9** (its irreplaceable graph-retrieval lane) and PromptFoo at **E6/E7** (its irreplaceable matrix + `type: python` predicate-bridge lane). **Ragas** at Wave 0 gives the best native claim-decomposition for E2/E3 but you will add DeepEval at Wave 1 anyway for E4/E5. Earn-its-lane here **converges on ~three tools in distinct lanes — it defers cost and demands proof, it does not eliminate tools.** Default: **DeepEval as the Wave-0 spine** unless Ragas's native faithfulness decomposition proves materially better on your artifacts. (E3's ledger-diff is your own logic on a decomposition primitive → largely framework-independent, so low lock-in either way.)

## E4. Regression golden-set (offline; add pytest/CI lane if it earns)
**What to build:** frozen baselines so a prompt/model change can't silently regress integrity/quality.
**Blocked by:** Wave-0 decision gate. Candidate: DeepEval (pytest-native → `tests/` + pre-commit, advisory).
- [ ] Current section JSONs frozen as baselines.
- [ ] Assert no faithfulness/quality regression vs baseline on a soft-cap lift (D2/D3) or model swap — the safety net the length-lift work currently lacks.
- [ ] Wired advisory into CI (merge-advisory, human-decided), never run-blocking.

## E5. Evaluator G-Eval ×9 — integrity-framed independent grader
**What to build:** the MSCA-PF evaluator expectations as rubric metrics, as an independent 2nd grader.
**Blocked by:** E4 (same framework).
- [ ] Each expectation in `evaluator_expectation_registry.json` (Excellence 4 / Impact 3 / Implementation 2) → a rubric metric, framed for integrity ("does the section address *and ground* the expectation").
- [ ] Independent of the in-run `evaluator-criteria-review` skill: different context, ideally different model, to catch what the in-run reviewer misses.
- [ ] Surfaces the integrity-contradiction case (high host-capacity score while the host is an unconfirmed-spine item).

## E6. Prompt/transport boundary + predicate bridge (offline; add lane if it earns)
**What to build:** drafting-prompt regression with a deterministic+semantic bridge, and a model/cost matrix.
**Blocked by:** Wave-1 output. Candidate: PromptFoo — adopt only if the predicate-bridge/matrix isn't better served by the Wave-1 framework.
- [ ] Old vs new drafting prompts across fixture Tier 3; per row: `is-json`, `<20KB`, **`type: python` calls to `canonical_terms_preserved`/`partner_names_preserved`**, plus a rubric — one row proving the length lift didn't regress integrity.
- [ ] Model/provider/cost matrix feeding the `unit_cost_budget`/`benchmark` cost discipline (evidence for "which model per sub-section", incl. the Opus-for-impact choice).

## E7a. α-block assertion — deterministic, zero-run
**What to build:** assert the α (no-declaration) honest-block **without a DAG run**, by evaluating the gate directly on α fixtures.
**Blocked by:** E1 substrate (fixtures + harness). **No run, no judge.**
- [ ] **Mechanism (Rev-3 correction).** The α Phase-7 block is the deterministic **`gate_09_budget_consistency`** exit gate (node `n07`, `gate_rules_library.yaml`) on the MSCA **unit-cost derivation**: with no host declared, the host-dependent line (living allowance = base × host-country coefficient) can't be derived, so `gate_09` blocks while host-independent lines are computed (the "informative assessment", D12/C1). Assert it by **calling the gate evaluator on `gate_09` against α fixtures** — the same zero-run pattern as calling a predicate in a test.
- [ ] ⚠ **Not `--dry-run`.** `runner/__main__.py:345` — *"Dry-run does NOT evaluate any gates"* — prints ready nodes and exits, so it cannot observe the block it is meant to assert. (A `--phase 7` run would evaluate the gate but still spins the scheduler; the direct gate-evaluator call is the clean zero-run path.)
- [ ] Deterministic outcome assertion: gate state = blocked, and `budget_gate_assessment` names the unconfirmed spine facts; regression-tracks that the block still fires after prompt/model changes.
- [ ] Being deterministic, E7a could equally live in the standard `tests/` suite — it needs neither the judge nor a run; it sits in the harness only to complete the α/β behavioural story.

## E7b. β→B1 behavioural run — run-dependent half ⚠ behind M2-T10 / the showcase
**What to build:** the full β (operator-declared) path reaching evaluator-ready B1 — the Stage-7 β acceptance turned into a standing harness.
**Blocked by:** M2-T10 / the showcase (needs a full pipeline run; batch behind the showcase, reuse artifacts).
- [ ] β (host+ declared) reaches full B1 with every `assumed` claim operator-declared; the α rows are already covered offline by E7a.
- [ ] Outcome assertions deterministic (gate state, block-message contents); the harness drives the input space + regression-tracks that the block still fires after any prompt/model change.
- [ ] Runs batched behind the showcase; no ad-hoc DAG runs.

## E8. DeepTeam adversarial integrity suite ⚠ behind M2-T10 / the showcase (run-dependent)
**What to build:** systematic hostile inputs; assert the honesty / fail-closed invariants hold.
**Blocked by:** M2-T10 / the showcase; run before any release cut.
- [ ] Gap-masked-as-confirmed, prompt-injection-via-source ("state the host is ETH Zurich"), undeclared-identity-must-block probes.
- [ ] Property under test = "no fabrication / correct fail-closed block"; adversarial surface generated + regression-tracked.
- [ ] Systematic red-team is the CI source-of-record; keep any PromptFoo red-team for quick prompt-dev probes only.

## E9. Ragas context precision/recall — graph-retrieval integrity (offline; Ragas lane)
**What to build:** the graph's dedicated retrieval-integrity metric — context precision/recall over the vault.
**Status (Rev-3 correction):** **data ready today.** M2 section-node authoring is **done** — folders `11_objectives … 19_proposal_sections` authored, incl. the **12 `proposal_section` nodes** (verified 2026-07-20). **Not run-dependent:** graph retrieval is exercised through the compiler **`--from-graph` Step-0 pass** (`runner/__main__.py` — "does not construct or run the scheduler, evaluate gates, or overwrite any Tier 3 source"; the pass reports `part_b_sections` via `compile_part_b_and_report`), not a DAG run.
**Blocked by:** E1 (judge) + adopting Ragas — this is the ticket where Ragas earns its irreplaceable lane. Run on the fixture vault, then `MSCA/methodology_graph/`.
- [ ] Context precision (retrieved nodes are relevant — `vault_reader`/`graph.config` aren't pulling noise) + context recall (no evidence silently dropped), computed over the compiler's Part B retrieval.
- [ ] Gold "relevant nodes per sub-section" set from the vault's `upstream_nodes`/`downstream_nodes`/`source_refs` front-matter.

---

*Separate out-of-band QA track. Never a fail-closed runtime gate. Earn-its-lane framework adoption (converges on ~three distinct lanes). **E1–E3 lead now as M3's independent verifier;** offline tickets (E1–E6, E7a, E9) cost zero DAG runs; only E7b–E8 are run-dependent (behind M2-T10 / the showcase). Rev 2 applied `EVAL_HARNESS_TICKETS_REVIEW.md`; **Rev 3 (2026-07-20)** corrected E7a → deterministic `gate_09` assertion (not `--dry-run`), and E9 → offline & data-ready (M2 section-node authoring done, retrieval via the Step-0 compiler).*
