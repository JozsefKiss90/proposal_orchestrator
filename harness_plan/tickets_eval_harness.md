# Tickets: Evaluation & Integrity Harness — out-of-band QA track

Source strategy: `EVALUATION_HARNESS_STRATEGY.md` (v1, 2026-07-20). Reviewed in `EVAL_HARNESS_TICKETS_REVIEW.md` (2026-07-20). **Rev 2** applied that review (E1–E3 lead as M3's verifier; **E1.5** judge-reliability; `ticket 10 → M2-T10`; E7 split; E3 materiality). **Rev 3 (2026-07-20)** corrects two items on code verification:

- **E7a mechanism.** `--dry-run` does **not** evaluate gates (`runner/__main__.py:345` — *"Dry-run does NOT evaluate any gates"*); it prints ready nodes and exits. The α Phase-7 block is the deterministic **`gate_09_budget_consistency`** exit gate (node `n07`) on the MSCA unit-cost derivation — assert it by calling the gate evaluator directly on α fixtures (zero run, no judge). E7a rewritten.
- **E9 unblocked + offline.** The M2 **section-node authoring is done** — vault folders `11…19` are authored incl. the **12 `proposal_section` nodes** (verified 2026-07-20). Graph retrieval runs through the compiler `--from-graph` **Step-0 pass, not a DAG run**. E9 moves out of the run-dependent bucket into the offline track.

**Rev 4 (2026-07-21) — build status + framework resolution.** **E1, E1.5, E2 are implemented, reviewed, and committed** on branch `harness` (E1 `4d0a73e`, E1.5 `1f9df59`, E2 `f75d9e0`). The Wave-0 framework question is **resolved: E2 is native** on the E1/E1.5 substrate, no framework dependency — this **supersedes the earlier "DeepEval as Wave-0 spine" default** (rationale in the decision-gate cascade below; recorded in the decision log). Plan docs now live in `harness_plan/`. One open item carries forward: E1.5's gold set **ships unlabeled** — human labeling + the first calibration run is the pending deliverable that graduates the judge (and E2) from advisory.

**Rev 5 (2026-07-21) — build reality + cost policy + coordination.** **E3 (`b2b69b0`) and E4 (`1f85fe6`) are implemented, reviewed, and committed** on branch `harness`; Wave 0 is complete and Wave 1's E4 is done (native). This Rev folds in decisions that until now lived only in the `harness_plan/` companion docs — invisible to build sessions, the coordination gap it closes: **E3.1** (materiality calibration → advisory→gating for E3), **E10** (the single deferred paid/online-framework ticket), the **subscription cost policy**, and E4's grounding-baseline open item. **LLM calls run on the Claude Code subscription plan (flat-rate — no per-call bill); the harness judge is a non-drafter local model. Runs incur no metered cost; the only added-cost item is E10's external frameworks.** Waves refreshed to reality.

> **Companion docs — read these; they carry the rationale, and this ticket folds in their decisions:** `harness_plan/EVAL_HARNESS_TICKETS_REVIEW.md` (strategy review), `EVAL_HARNESS_E3_PREAPPROVAL.md` (E3 grounded review + D1–D3 resolution), `HARNESS_COST_POLICY.md` ($0 policy + free/paid taxonomy + E10). If a companion doc and this ticket disagree, update both.

This is a **separate, out-of-band QA/CI track** — architecturally distinct from the runtime DAG and the milestone-2 authoring track. It sits alongside M3, not inside M2.

**Scope decision (operator steer): earn-its-lane phasing.** Prove the two headline integrity signals in one framework first; adopt a second/third framework only when its *distinct* lane demonstrates ROI; keep the right to consolidate. Integrity-weighted over quality.

## Referenced dependencies (pinned)

Pin every gating name so no ticket is gated on an undefined artifact (same fail-closed-on-dangling-links discipline `vault_reader.dangling_links()` applies to wikilinks).

- **`M2-T10`** = milestone-2 ticket 10 — the *graph-becomes-authoritative-Tier-3-source* cutover (open-Q #4, `tickets_milestone2.md`). Gates only the run-dependent **E7b/E8** (they reuse the showcase's runs). The offline tickets do **not** wait on it. **(M2 tickets 1–9 are ✅ complete; only T10 — E2E graph-sourced run + open-Q #4 — and T11 — B2 extension — remain.)**
- **M2 section-node authoring — ✅ DONE (verified 2026-07-20).** The milestone-2 ticket that authors `proposal_section` nodes has authored vault folders `11_objectives … 19_proposal_sections`, including the **12 `proposal_section` nodes** (PS-excellence-1/1.1–1.4, PS-impact-2/2.1–2.3, PS-implementation-3/3.1–3.2). E9's authoring blocker is **cleared**. (The `GRAPH_SUBSTRATE.md` "walking-skeleton / folders 11–18 unauthored" note is stale — supersede it.)
- **"the showcase"** = the planned flagship end-to-end run (M2 graph-sourced Tier 3 + M3 composition + Opus-for-impact Impact authoring) that produces an evaluator-ready Part B, whose runs **E7b/E8** batch behind. ⟐ now **pinned = the Phase-8 finalization re-run** (M2 graph-sourced + refreshed Tier 3 + Opus-for-impact) that clears `gate_10b_impact_completeness` and produces an evaluator-ready Part B. The run is on the Claude Code subscription (flat-rate) — no metered bill.
- **"Opus-for-impact"** = authoring/composing the Impact section with the Opus model (the model choice E6's cost matrix is meant to evidence). Now **activated to clear `gate_10b_impact_completeness`** — Opus 4.8 runs on the Claude Code subscription (flat-rate), so no cost tension. The anti-fabrication guard still applies: every impact claim must trace to the refreshed Tier 3 (exactly what E2/E3 verify).

## Non-negotiable guardrails (span every ticket)

- **Never a fail-closed runtime gate.** No eval metric wires into the runtime DAG. The 138 predicates + byte-equal CI checks remain the only blocking runtime gates (§17 byte-equal replay + fail-closed preserved). The harness gates *decisions about the pipeline* — merges, prompt changes, model swaps, release cuts — in CI, and even there it is **advisory to a human**, not auto-blocking, until judge reliability is characterized (**E1.5**).
- **Deterministic-first routing.** Where a predicate/gate can check a property, it is authoritative; a judge runs only where no deterministic check exists; a green judge never overrides a red predicate. *(E7a is a case in point — the α-block is a deterministic gate, so it is asserted deterministically, no judge.)*
- **Grader–generator independence.** Judge with a non-drafter model over the OpenAI-compatible transport.
- **Judge output is `Inferred`, never `Confirmed`.** Pin judge model+version, temp 0, N≥3 majority where a score informs a decision; log `{judge_model, judge_version, prompt_hash, score, rationale}` as provenance (same discipline as the decision log).
- **Earn-its-lane.** Each framework must prove its distinct lane before the next is adopted. If a lane is better served by a framework already in use, do not add the second tool. (Expect convergence on ~three tools in *distinct* lanes — see the Wave-0 decision gate.)
- **API currency.** Exact Ragas/DeepEval/PromptFoo metric/API names predate the May-2025 cutoff — confirm against current docs at build time before writing any binding (Inferred until then). *(This is a live constraint: the frameworks are absent from the offline build env, so a real binding can't be verified here — a reason E2 went native.)*
- **Cost policy (Rev 5) — subscription + local judge.** Claude LLM calls run on the Claude Code subscription (flat-rate, no per-call bill); every harness feature unit-tests with a fake backend and runs against a non-drafter local judge — no feature may require a *separately-metered* provider. Only external frameworks that call their own metered endpoints (DeepEval, Ragas LLM-graded, PromptFoo provider matrix, DeepTeam) defer to **E10**. Full taxonomy: `harness_plan/HARNESS_COST_POLICY.md`.

## Sequencing — the "avoid extra runs" split

The harness judges **artifacts, not runs** — almost all of it never triggers a DAG run.

- **Offline tickets (E1–E6, E7a, E9)** read frozen artifacts, exercise the deterministic gate evaluator, or run the Step-0 graph compiler. **Zero DAG runs.** E1–E3 lead now (M3's verifier); E7a is a deterministic `gate_09` assertion; **E9's graph data is authored and reached via the `--from-graph` compiler pass, not a run.**
- **Run-dependent tickets (E7b, E8)** observe β→B1 / hostile-input behaviour that needs full pipeline runs. **Gated behind M2-T10 / the showcase:** batch their runs behind the showcase and reuse its artifacts — never ad-hoc. This is where "avoid running phases more than necessary" is enforced.

**Why E1–E3 lead (review MF-1 — the M3 collision).** M3 introduces a **Claude-driven composition pass** that rewrites each section's `content` (de-identify + weave to evaluator-ready prose) while carrying `claim_statuses`/`source_ref` forward **verbatim**. Its anti-fabrication guarantee is *not* determinism (the composer is synthesis — `MILESTONE3_SCOPE.md` §7 calls it a sanctioned "shadow author") but the structural contradiction-detector gates + `no_unsupported_tier5_claims` — the latter itself a **semantic/in-run** gate (absent from the deterministic predicate registry), i.e. the same-model-family judge the strategy §2 says must not be trusted alone. Those gates catch a *wrong* token, not a composer that keeps every canonical token but subtly **weakens the grounding** of a `confirmed` claim. **E2 status-aware faithfulness is exactly that missing check.** So E1–E3 are built **before** M3 composition and reused as the exit check on **M3-T3 / M3-T7** — the independent, out-of-band net M3's §7 risk calls for. *Baseline nuance:* baseline Excellence + Implementation immediately; baseline Impact **after** the Opus-for-impact authoring (the one section that genuinely changes), so you are not diffing against a to-be-discarded version.

## Waves

- **Wave 0 (offline — M3's verifier; core proven native):** ✅ E1 · ✅ E1.5 *(mechanism; ⏳ gold-set labeling)* · ✅ E2 · ✅ E3 *(`b2b69b0`)* — all **native**. Decision gate passed: no second framework adopted.
- **Wave 1 (offline):** ✅ E4 *(`1f85fe6`, native; ⏳ grounding baselines unfrozen)* · ⏸ E5 → **native rubric grader = $0; DeepEval form → E10**.
- **Graduation track (advisory → gating; $0 on local judge):** ☐ **E1.5 gold-set labeling** · ☐ **E3.1 materiality calibration**. Until these land, the E2/E3/E4 judge lanes stay advisory.
- **Wave 2 (offline):** ☐ E6 *(native predicate bridge = $0; provider matrix → E10)* · ☐ E7a *(deterministic; no judge, no run)*.
- **Wave 3 (offline, graph-retrieval):** ☐ E9 → **native set-math core = $0; Ragas LLM-form → E10**.
- **Wave 4 (run-dependent — behind M2-T10 / the showcase; runs on the subscription, no metered bill):** ☐ E7b · ☐ E8 *(DeepTeam generation → E10)*.
- **E10 (deferred):** paid/online framework integration — gated on budget + an online session.

Runs are covered by the Claude Code subscription (no metered bill); the only remaining cost line is E10's external tooling.

---

## E1. Harness substrate + independent judge config — ✅ DONE (`4d0a73e`, branch harness)
**What to build:** the out-of-band scaffolding every metric stands on.
**Blocked by:** none (offline).
- [x] A pinned non-drafter judge over the OpenAI-compatible transport (temp 0; model+version pinned). → `harness/judge.py`
- [x] Provenance logging `{judge_model, judge_version, prompt_hash, score, rationale}` for every verdict. → `harness/provenance.py`
- [x] A deterministic-first routing helper: a property with a predicate/gate is never judged; the judge runs only in the semantic gap. → `harness/routing.py`
- [x] Reporting-only output (no CI gate yet); a documented "never a runtime gate / advisory-to-human" boundary. → `harness/report.py` + `HARNESS.md`
- [x] Judge output typed `Inferred`; N≥3 majority scaffold where a score will inform a decision. → `harness/verdict.py`
- [x] Structural guarantee: one-way dependency (harness → runner, never runner → harness), enforced by a boundary test.

## E1.5 Judge-reliability calibration — the "advisory → gating" mechanism — ✅ DONE *(mechanism; `1f9df59`, branch harness)* · ⏳ pending human labeling
**What to build:** the meta-eval that characterizes judge reliability, so a metric can graduate from advisory to merge-gating and the `Inferred` scores carry a calibration basis. Without it, the guardrail's "advisory until judge reliability is characterized" clause has no mechanism and the harness is permanently advisory by default.
**Blocked by:** E1.
- [x] Gold-set loader + seeder built (`gold_set.py`) — 30 stratified, deduped candidates from `excellence_section.json`; fail-closed on unlabeled pairs; `supported` is the human ground truth, never the engine's status. ⏳ **The set ships unlabeled** (`gold_sets/…_TEMPLATE.jsonl`) — **human labeling + the first calibration run is the pending deliverable** that graduates the judge (an AI labeling gold for an AI judge would reintroduce the very correlation the harness avoids).
- [x] Measure precision/recall on faithfulness verdicts vs the gold set; record `{judge_model, judge_version, precision, recall}`. → `calibration.py` + `faithfulness.py` (runs once labels exist).
- [x] Define the graduation threshold; advisory until cleared, no auto-gating. → `graduation_for()` (fail-safe cascade: no calibration / repinned judge / below-threshold → advisory).
- [x] Re-run on any judge model/version repin (a repin re-opens advisory). → `CalibrationReport.applies_to` + `CalibrationLog`.

## E2. Status-aware faithfulness — headline signal #1 — ✅ DONE (`f75d9e0`, branch harness) · **native**
**What to build:** faithfulness partitioned by claim status — the "gap masked as confirmed" detector; **also reused as M3-composition's exit check.**
**Framework:** **native** on the E1/E1.5 substrate — no framework dependency (`harness/status_faithfulness.py`). Resolved at the decision gate below; DeepEval/Ragas deferred to E5/E8/E9. **Advisory until E1.5 is labeled + calibrated** (blocking=False by construction).
**Blocked by:** E1 (built on it).
- [x] Claims partitioned by `status`; `confirmed` → judged strictly vs its `source_ref`; unsupported = hard `SEVERITY_INTEGRITY` finding — the "gap masked as confirmed" no predicate can see.
- [x] `assumed` → judged vs the `working_assumptions.json` declared value, not the source (complements W1: existence → content).
- [x] `inferred` → framing/synthesis under a softer bar.
- [x] Un-verifiable claims surfaced, never dropped; boolean primary, a score only refines the bar under an N≥3 majority (no single sample fires a hard finding); truncation made loud (a truncated source can't manufacture a false integrity finding).
- [x] Built against the current `excellence/impact/implementation_section.json` (real-data probe: all 406 claim refs resolve, 0 unresolved / 0 truncated); re-points at M2-T10's graph-sourced artifacts unchanged. Reporting-only; zero DAG runs.
- [x] **M3 reuse:** `freeze_baseline` / `compare_to_baseline` — per-claim grounding-invariance for the M3-T3/T7 exit check.

## E3. Claim-ledger completeness + status calibration — headline signal #2 — ✅ DONE (`b2b69b0`, branch harness) · **native**
**What to build:** the "escaped claim" detector + calibration drift.
**Status: ✅ DONE** — native (`harness/claim_ledger.py`, `materiality.py`, `status_calibration.py`); matches by *meaning*, never bare `claim_id` (D1); materiality precision `None` until negatives labeled (→ **E3.1**). Boxes below are the as-built spec; full D1–D3 resolution in `harness_plan/EVAL_HARNESS_E3_PREAPPROVAL.md`.
**Blocked by:** E1 (built on the same **native** substrate as E2). ⟐ **Framework re-opens here on its own merits:** prose→atomic-assertion decomposition is the one place a framework's differentiator (Ragas) *or* a native decomposition-judge applies — decide when E3 is built; the ledger-diff is custom either way, so native is the likely answer.
- [ ] Prose decomposed into atomic assertions, diffed against logged `claim_id`s; a non-empty "unledgered assertion" set is a hard finding ("fabricates without emitting a claim" — the threat W1 cannot reach).
- [ ] **Materiality threshold (else self-defeating; the design task to settle first).** Only assertions meeting the *material claim* bar must map to a `claim_id`; non-material prose (transitions, framing, definitional/method description) is excluded — else the "escaped claim" set floods with false positives and the check gets ignored. **Two anchors, spelled out:**
    - *Constitutional (the mandate) — `CLAUDE.md` §10.5, verbatim:* "All major outputs produced by agents must be traceable to their tiered inputs. An agent must be able to identify, for each material claim in its output, the Tier 1–4 source from which the claim derives. **Unattributed claims must be flagged, not asserted.**" → **E3 is the output-side checker for that final sentence** — an "escaped claim" *is* an unattributed material claim, and no predicate currently enforces it on the prose (the source-ref predicates check the *field* exists, not that every material assertion has one). Strong charter — but §10.5 is the term's *only* occurrence in the constitution and never defines *which sentences count*; `claim_statuses` carries no `material` flag.
    - *Empirical (the operational bar).* Derive materiality from the **406-claim ledger** — the engine's own enumeration of what it treats as material-and-attributable. Calibrate the classifier against it (positives = real `claim_summary` values; negatives = framing/transition/definitional spans); flag prose assertions that clear that bar yet match no `claim_id`. In one line: **§10.5 says *what* (material claims must be attributed or flagged); the ledger says *which*.**
- [ ] Claim-status calibration: a `confirmed` that isn't grounded, or an `inferred` fully source-backed (mislabelled down), flagged as drift.
- [ ] Runs on the real section as a ready-made calibration set; reporting-only; zero runs.

### ⟐ Earn-its-lane decision gate (after Wave 0)
Did status-aware faithfulness + ledger completeness surface real issues (or give real confidence) on the current artifacts? Record the finding in the decision log. Only if yes — and only for a *distinct* capability — adopt a second framework in Wave 1. If the chosen framework underdelivered, reconsider it before adding tools.

**Framework boundary — RESOLVED at E2 (native).** E2 was built **native on the E1/E1.5 substrate**, no framework dependency (`f75d9e0`; decision recorded in the decision log). Why native, not the earlier "DeepEval-spine" default: (i) the engine already emits **pre-decomposed** `claim_statuses`, so no framework's headline claim-decomposition differentiator applies at E2; (ii) the substrate already carries the atomic support-judge (E1.5 `faithfulness.py`) — adopting a framework would wrap/duplicate the judge just de-duplicated; (iii) the **API-currency guardrail** blocks a *verifiable* DeepEval/Ragas binding in the offline build env. This **supersedes "DeepEval as the Wave-0 spine."** The resolved boundary — earn-its-lane still converges on ~three tools in distinct lanes, just none of them at E2–E4/E7a:

- **E2 → native** (done). **E3 → native** likely (decomposition question re-opens on its own merits; ledger-diff is custom regardless). **E4 → native** (regression reuses E2's `freeze_baseline`/`compare_to_baseline`). **E7a → deterministic** gate call.
- **DeepEval → E5 (G-Eval rubrics) + E8 (DeepTeam)** — its real differentiators; adopt in an **online** build session that can satisfy the API-currency guardrail.
- **Ragas → E9** — graph context precision/recall (retrieval-eval machinery).
- **PromptFoo → E6/E7** — provider matrix + the `type: python` predicate bridge.

## E3.1 Materiality calibration completeness — advisory→gating for E3 (offline; native; $0 on local judge)
**What to build:** the measurement that graduates E3's materiality signal from advisory — mirrors E1.5 for the judge. Folded in from `harness_plan/EVAL_HARNESS_E3_PREAPPROVAL.md` (D2).
**Blocked by:** E3 (built on it). Does **not** block E4.
- [ ] Label `harness/materiality_sets/materiality_negatives_TEMPLATE.jsonl` (non-material spans) → compute + record **precision** `{judge_model, judge_version, precision}`. (Positives-only precision stays `None` by design — a spurious 1.0 otherwise.)
- [ ] Seed a small human-labeled set of **out-of-ledger material claims** (material assertions deliberately absent from the ledger) → compute + record **recall / miss-rate** on the real failure mode. (Overlaps E8 fixtures — minimal set here; also the first fixtures exercising the `assumed` path, still 0 in real data.)
- [ ] Apply the E1.5 `graduation_for` threshold → record the graduation decision (advisory-stays / promote-to-gating) in the decision log.
- [ ] Human ground truth only; reporting-only; zero runs. **$0** on the local judge.
**Done =** E3's precision + miss-rate are characterized and a graduation decision is recorded — not necessarily promotion.

## E4. Regression golden-set — ✅ DONE (`1f85fe6`, branch harness; offline; native)
**What to build:** frozen baselines so a prompt/model change can't silently regress integrity/quality.
**Blocked by:** Wave-0 decision gate. **Native** on the substrate — the harness already runs under pytest (238 tests) and E2 ships `freeze_baseline`/`compare_to_baseline`; E4 formalizes that into a standing golden-set suite. (No framework: DeepEval's pytest-integration isn't needed here — it earns in at E5.)
- [x] Current section JSONs frozen → `harness/regression_baselines/*.golden.json` (full 406-entry ledger). Diff matches claims by **meaning** — `(claim_summary, status, source_ref)`, never bare `claim_id` (the E3 lesson). Empty golden dir fails closed (a check against no baselines can't vacuously pass).
- [x] No-regression assertion, **two lanes:** deterministic fingerprint lane (zero judge, offline) classifying breaking vs advisory drift; **judge lane** = thin wrappers over E2's `freeze_baseline`/`compare_to_baseline` (grounding invariance).
- [x] Wired advisory into CI — **"CI" = the pytest suite** (`tests/harness/test_regression_golden.py`, marker `harness_regression`; repo has no hosted CI config). `RegressionReport` enforces `advisory=True, blocking=False`; nothing in `runner` reads it. CLI: `py -3.10 -m harness.regression freeze|check`.
- [ ] ⏳ **Open item:** grounding baselines are **not frozen yet** — the judge lane is machinery-only until the live pinned **local** judge freezes them. Now unblocked ($0, local judge).

## E5. Evaluator G-Eval ×9 — integrity-framed independent grader — ⏸ DEFERRED shape: **native rubric grader = $0; DeepEval framework form → E10**
**What to build:** the MSCA-PF evaluator expectations as rubric metrics, as an independent 2nd grader.
**Blocked by:** E4. **First DeepEval adoption** (G-Eval is a DeepEval primitive) — do it in an online build session so the API-currency guardrail can be satisfied; else fall back to a native rubric judge on the substrate.
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
**Blocked by:** M2-T10 / the showcase; run before any release cut. (DeepEval/DeepTeam adoption — online build session for API currency.)
- [ ] Gap-masked-as-confirmed, prompt-injection-via-source ("state the host is ETH Zurich"), undeclared-identity-must-block probes.
- [ ] Property under test = "no fabrication / correct fail-closed block"; adversarial surface generated + regression-tracked.
- [ ] Systematic red-team is the CI source-of-record; keep any PromptFoo red-team for quick prompt-dev probes only.

## E9. Ragas context precision/recall — graph-retrieval integrity (offline) — **native set-math core = $0; Ragas LLM-graded form → E10**
**What to build:** the graph's dedicated retrieval-integrity metric — context precision/recall over the vault.
**Status (Rev-3 correction):** **data ready today.** M2 section-node authoring is **done** — folders `11_objectives … 19_proposal_sections` authored, incl. the **12 `proposal_section` nodes** (verified 2026-07-20). **Not run-dependent:** graph retrieval is exercised through the compiler **`--from-graph` Step-0 pass** (`runner/__main__.py` — "does not construct or run the scheduler, evaluate gates, or overwrite any Tier 3 source"; the pass reports `part_b_sections` via `compile_part_b_and_report`), not a DAG run.
**Blocked by:** E1 (judge) + adopting Ragas (online build session for API currency) — this is the ticket where Ragas earns its irreplaceable lane. Run on the fixture vault, then `MSCA/methodology_graph/`.
- [ ] Context precision (retrieved nodes are relevant — `vault_reader`/`graph.config` aren't pulling noise) + context recall (no evidence silently dropped), computed over the compiler's Part B retrieval.
- [ ] Gold "relevant nodes per sub-section" set from the vault's `upstream_nodes`/`downstream_nodes`/`source_refs` front-matter.
- [ ] **Native $0 path:** with that gold set, context precision/recall is **set arithmetic on node IDs** — no judge, no embeddings. Ragas's LLM-graded form (if ever wanted) → E10.

## E10. Paid / online framework integration — ⏸ DEFERRED (single ticket)
**What:** adopt the external frameworks whose value is inseparable from billed calls — DeepEval (G-Eval / DeepTeam), Ragas (LLM-graded context metrics), PromptFoo (provider/cost matrix). Folded in from `harness_plan/HARNESS_COST_POLICY.md`.
**Gated by:** (a) available budget, and (b) an online build session (satisfies the API-currency guardrail). Never a runtime gate.
**Free cores already in the native track (do NOT wait on E10):** E5 → native rubric grader; E9 → set-math context precision/recall; E6 → native predicate bridge; E7a → deterministic α-block; E8 honesty invariants → hand-authored fixtures + deterministic block assertions.
**Scope when funded:** framework bindings + provider/cost matrix + DeepTeam generation + any remaining adversarial runs. One ticket, one budget line.

---

*Separate out-of-band QA track. Never a fail-closed runtime gate. Earn-its-lane framework adoption (converges on ~three distinct lanes). **E1–E3 lead as M3's independent verifier;** offline tickets (E1–E6, E7a, E9) cost zero DAG runs; only E7b–E8 are run-dependent (behind M2-T10 / the showcase). Rev 2 applied `EVAL_HARNESS_TICKETS_REVIEW.md`; Rev 3 (2026-07-20) corrected E7a → deterministic `gate_09` assertion and E9 → offline & data-ready; **Rev 4 (2026-07-21): E1/E1.5/E2 done & committed (branch `harness`); framework resolved — E2 native, superseding the DeepEval-spine default (DeepEval → E5/E8, Ragas → E9, PromptFoo → E6/E7); E4 native. Open: label E1.5's gold set to graduate E2 from advisory. **Rev 5 (2026-07-21): E3 (`b2b69b0`) + E4 (`1f85fe6`) done & Waves refreshed; folded in E3.1, E10, the subscription cost policy, E4's grounding-baseline open item, and the companion-doc pointer — closing the gap where these lived only in `harness_plan/`. pipeline on the Claude Code subscription; harness judge local; only E10 adds metered cost.***
