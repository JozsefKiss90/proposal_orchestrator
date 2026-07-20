# Review — Eval & Integrity Harness tickets (`tickets_eval_harness.md`)

> **Reviewed 2026-07-20** against `EVALUATION_HARNESS_STRATEGY.md` (v1), the strategy's source code base (`runner/predicates/**`, `evaluator_expectation_registry.json`, `excellence_section.json`), and the surrounding roadmap (`MILESTONE3_SCOPE.md`, `tickets_milestone2.md`). Confidence **Confirmed** unless marked.
>
> **Rev-note (2026-07-20, post-verification):** the operator flagged two items; both were checked against the code and **corrected** — see **Corrections** immediately below. They supersede R-4's dry-run mechanism and MF-2's E9 run-classification; the rest of the review stands.

## Corrections (post-verification, 2026-07-20)

Two items were verified against source and **corrected** — folded into `tickets_eval_harness.md` Rev 3.

1. **E7a mechanism — supersedes R-4's "`--dry-run` / single-phase" suggestion.** `--dry-run` does **not** evaluate gates (`runner/__main__.py:345` — *"Dry-run does NOT evaluate any gates"*; it prints ready nodes and exits), so it cannot observe the α block. The α Phase-7 block is the **deterministic** `gate_09_budget_consistency` exit gate (node `n07`, `gate_rules_library.yaml`) on the MSCA **unit-cost derivation**: with no host declared, the host-country-coefficient line can't be derived, so `gate_09` blocks (host-independent lines still computed = the informative assessment, D12/C1). Assert it by calling the **gate evaluator directly on `gate_09` against α fixtures** — still zero-run, and *deterministic* (no judge). R-4's intent (E7a is offline, no full run) held; its mechanism was wrong.

2. **E9 is neither blocked nor run-dependent — supersedes MF-2's E9 dependency note.** The "folders 11–18 unauthored / walking-skeleton" premise (from `GRAPH_SUBSTRATE.md`) is **stale**: the M2 section-node authoring is **done** — vault folders `11_objectives … 19_proposal_sections` are authored, incl. the **12 `proposal_section` nodes** (verified 2026-07-20). Graph retrieval runs through the compiler `--from-graph` **Step-0 pass** (`__main__.py` — "does not construct or run the scheduler, evaluate gates, or overwrite any Tier 3 source"), **not a DAG run**. So E9's data is ready today and it gates only on adopting Ragas + the E1 judge — it moves **out of the run-dependent Wave 4 into the offline track**. MF-2's separate-the-dependencies instinct held (M2-T10 ≠ section-node authoring); the correction is that the authoring is complete and the retrieval path is Step-0.

Read the E7 and E9 rows of the alignment table (§5) through these corrections.

## Verdict

**The approach is right, and the tickets trace faithfully to the plan.** Earn-its-lane phasing, the out-of-band/never-a-runtime-gate spine, deterministic-first routing, grader–generator independence, and `Inferred`-not-`Confirmed` scoring are all carried through — and in two places *strengthened* (the "advisory-to-human until judge reliability is characterized" clause, and the offline/run-dependent split that keeps most of the harness at zero DAG-run cost). All eleven strategy metrics appear across E1–E9. Nothing in the ticket set contradicts the strategy.

The concerns are about **sequencing and traceability, not content.** Two are worth treating as must-fixes before this set is locked; the rest sharpen tickets that are already directionally correct.

- **MF-1 — Pull E1–E3 ahead of ticket 10 / M3.** As sequenced, the harness's headline integrity signals land *after* the change they exist to guard. This forfeits their highest-value use and leaves M3's riskiest step unguarded. Low-cost to fix (offline, zero runs).
- **MF-2 — Pin the dangling references.** "Ticket 10", "the showcase", and "the Opus-for-impact authoring" gate E7–E9 but are not linked to canonical ticket IDs; two of the three appear in no repo doc at all. In a system whose ethos is traceability, a ticket gated on an undefined artifact is an unresolved dependency.

Everything below is either endorsement (§1), the two must-fixes (§2–§3), or ticket-level refinements (§4), with an alignment table (§5).

---

## 1. What's right — endorse as-is

- **Out-of-band, never a fail-closed runtime gate.** Correctly the load-bearing invariant. The guardrail block restates it precisely (138 predicates + byte-equal checks stay the only blocking runtime gates; the harness is advisory-to-human in CI). This is the single most important thing to get right for *this* system, and the tickets get it right.
- **Earn-its-lane is a good fit for your culture.** It mirrors how you deferred the Obsidian graph "in toto" until it earned its place on authoring/traceability rather than length. Proving one framework on the two headline signals before adopting a second is disciplined and cost-aware.
- **"Judge artifacts, not runs" + the offline/run-dependent split (E1–E6 vs E7–E9).** This is exactly the right axis to sequence on, and it is what makes ~two-thirds of the harness cost-free. Good.
- **The guardrails carry the strategy's §2/§10 faithfully:** deterministic-first routing, non-drafter judge over the OpenAI-compatible transport, pinned model + temp 0 + N≥3 majority, provenance logging `{judge_model, judge_version, prompt_hash, score, rationale}`. No notes.

---

## 2. MF-1 — Sequencing E1–E3 behind ticket 10 is backwards for the stated goal

**The internal tension.** Line 20 says the offline tickets "will catch any regression the Opus-impact authoring introduces," yet sequences them *behind* ticket 10 (and the authoring). That is a smoke detector installed after the fire. The "can be pulled earlier at no run-cost if desired" clause already anticipates the fix; this recommendation is to elevate it from an option to the plan of record for E1–E3.

**Why it matters more than a normal regression guard — the M3 collision.** `MILESTONE3_SCOPE.md` is explicit that M3 introduces a **Claude-driven narrative-composition pass** that rewrites each section's `content` (de-identify + weave to evaluator-ready prose) while carrying `claim_statuses` + `source_ref` **forward verbatim**. Its anti-fabrication guarantee is *not* determinism (the composer is synthesis — §7 calls it a sanctioned "shadow author") but **gated verification**: the structural contradiction-detectors (`partner_names_preserved`, `canonical_terms_preserved`, `measurable_targets_preserved`, …) plus `no_unsupported_tier5_claims`, re-run on the composed output.

Two gaps in that guarantee are exactly what E2/E3 fill:

1. **The structural gates are token/appositive detectors.** They catch a *wrong* legal name or a *dropped* metric token. They do **not** catch a composer that keeps every canonical token but subtly *weakens the grounding* of a `confirmed` claim while rephrasing for flow. **E2 status-aware faithfulness is precisely that check** — it verifies the composed sentence still entails from its `source_ref`. Run E2 on pre-M3 prose → per-claim faithfulness baseline; re-run on post-M3 composed prose → faithfulness must be invariant. Any drift is a composition-induced integrity regression no structural gate can see.

2. **`no_unsupported_tier5_claims` — M3's semantic floor — is itself an in-run LLM gate** (it does not appear in the deterministic predicate registry `runner/predicates/__init__.py`; per your PHASE8 brief §6 and M3 §4 it is a "semantic gate"). That is the same in-pipeline, same-model-family judge your strategy §2 warns must not be *trusted alone*. E2/E3, run out-of-band with an independent judge, are the mitigation the strategy prescribes for exactly this situation. *(Confidence: Confirmed that `no_unsupported_tier5_claims` is absent from the deterministic registry; Inferred that it is realized as an LLM/skill gate — verify at build time.)*

So E1–E3 are not "QA we'll get to after the showcase." They are **the independent verifier M3-T3/M3-T7 structurally need.** Deferring them behind ticket 10 runs the riskiest architectural change on the board (synthesis re-entering the Tier-5 path) without the one net designed to catch its failure mode.

**Recommendation.**
- Build **E1–E3 now**, offline, against the current `msca-pf-syn-01` artifacts; freeze a per-claim faithfulness + ledger baseline. Zero DAG runs — the "no run-cost" clause already permits it.
- Re-run E2/E3 as the **exit check on M3 composition** and again after the ticket-10 cutover; require per-claim faithfulness invariance. This makes E2/E3 do double duty as M3's semantic acceptance test.
- Baseline nuance: Excellence and Implementation are stable inputs to baseline immediately; **Impact will change under "Opus-for-impact"** — baseline Impact *after* that authoring, so you are not diffing against a to-be-discarded version. (This is the one place the "sequence behind" instinct is correct — but it argues for staggering by section, not deferring the whole offline wave.)

---

## 3. MF-2 — Pin the load-bearing cross-references (traceability of the tickets themselves)

The run-dependent gating hangs on three names that are under-specified:

- **"ticket 10"** = milestone-2 ticket 10, the graph-becomes-authoritative-Tier-3-source cutover (open-Q #4), per `tickets_milestone2.md`. Definable — but "ticket 10" is ambiguous across your three ticket sets (`tickets.md`, `tickets_milestone2.md`, and now the eval set). Write it as **`M2-T10`** everywhere.
- **"the showcase"** and **"the Opus-for-impact authoring"** appear in **no** repo doc (grep-confirmed across all staged docs; they occur only inside `tickets_eval_harness.md`). E7–E9 are gated on them, so they are unresolved dependencies. Either point them at a canonical ticket/scope line, or add a one-line definition (e.g. "the showcase = the planned M2-cutover + M3-composition + Opus-impact E2E run producing an evaluator-ready Part B").
- **Decouple E9's two dependencies.** E9 correctly lists "ticket 10 **+** section-node authoring (folders 11–18)" — but note **M2-T10 (Tier-3 cutover) ≠ authoring `proposal_section` nodes.** E9 (context precision/recall over retrieval) needs the *section-node authoring*, which `tickets_milestone2.md`/`GRAPH_SUBSTRATE.md` place at a later ticket (the folders 11–18 are unauthored today — the "walking-skeleton" note). Name that ticket, not just "ticket 10," or E9's dependency is wrong.

This is not pedantry for its own sake — it is the same fail-closed-on-dangling-links discipline your `vault_reader` applies to wikilinks (`dangling_links()` is recorded, not silently passed). Apply it to the ticket graph.

---

## 4. Ticket-level refinements (aligned, but sharpen)

**R-1 — E3 needs a materiality threshold (else it self-defeats).** "Decompose the prose into atomic assertions and diff against logged `claim_id`s" will over-fire: a Part B section is full of transitions, framing, and method description that are *not* material claims and correctly carry no `claim_id`. Without a materiality filter, the "unledgered assertion" set is mostly false positives and the check gets ignored. Reuse the constitution's existing notion of a **material claim** (the same materiality `no_unresolved_material_claims` / §10.5 "source for every material claim" already rely on) to define what *must* be ledgered. This is the difference between E3 being usable and being noise.

**R-2 — Add a judge-reliability characterization ticket (currently unticketed).** The guardrails promise "advisory… **until judge reliability is characterized**" and "N≥3 majority" — but no ticket actually characterizes it. Without a meta-eval measuring the judge's false-positive/false-negative rate on faithfulness verdicts against a small **human-labeled** gold set (~20–30 `(claim, source_ref, supported?)` pairs), you can never graduate any metric from advisory to merge-gating, and the `Inferred` scores have no calibration basis. Add this as **E1.5** (or an E1 acceptance criterion). It is the mechanism that gives the "until characterized" clause teeth, and it is cheap.

**R-3 — Make the Wave-0 framework choice's downstream consequence explicit.** E2 says "Ragas **or** a DeepEval custom metric — pick ONE," but the pick cascades and the ticket should say so:
- **DeepEval at Wave 0** consolidates hardest: it covers E2, E3, E4, E5 *and* E8 (via DeepTeam) in one framework/ecosystem (pytest-native, G-Eval and DAG-metric are DeepEval primitives). Ragas then only needs to earn in at **E9** (context precision/recall — its genuinely irreplaceable lane), and PromptFoo at **E6/E7** (provider matrix + the `type: python` predicate bridge — its irreplaceable lane).
- **Ragas at Wave 0** gives the best *native* claim-decomposition for E2/E3, but you will add DeepEval at Wave 1 anyway for E4/E5.

Set the expectation that **earn-its-lane here converges on ~three tools, each in a distinct lane — it defers cost and demands proof; it does not eliminate tools**, because the lanes (graph-retrieval / pytest-rubric+red-team / prompt-boundary+matrix) are genuinely distinct. My recommendation: **DeepEval as the Wave-0 spine** unless Ragas's native faithfulness decomposition proves materially better on your artifacts. (Note E3's ledger-diff is your own logic on top of a decomposition primitive, so E3 is largely framework-independent — low lock-in either way.)

**R-4 — Part of E7 is pullable offline (reduce the run-dependent surface).** The α case ("no declarations → Phase 7 must block, naming the unconfirmed spine") is a **gate-state outcome** on given Tier-3 + `working_assumptions.json` inputs. Your PHASE8 brief documents a `python -m runner … --dry-run` / single-phase invocation that yields a clean fail-closed gate error rather than a full run. So split E7 into **(a)** offline/single-phase block-state assertions (pullable early, cheap) and **(b)** the full β→B1 run (legitimately batched behind the showcase). Only (b) needs M2-T10.

**R-5 — Restate one-system-of-record-per-metric once ≥2 frameworks are live.** Earn-its-lane implicitly avoids triple-maintenance, but the moment (say) Ragas owns faithfulness and DeepEval owns G-Eval, add the explicit rule that DeepEval's *own* faithfulness metric does not also run as a second source of truth. One SoR per metric (strategy §3).

**R-6 — Note the one consciously dropped metric.** Strategy §4.4 (answer relevancy) has no ticket. That is a defensible cut (low value; overlaps E5's "does the section address the expectation"), but per your own "no silent caps" principle, record the drop in one line rather than leaving it implicit.

---

## 5. Ticket → strategy alignment

| Ticket | Strategy element | Status |
|---|---|---|
| Guardrails | §2 (determinism tension) + §10 (risks) | ✅ Faithful; strengthened |
| E1 substrate + judge | §2, §8 judge config | ✅ Aligned — add **R-2** judge-reliability calibration |
| E2 status-aware faithfulness | §4.1 | ✅ Aligned — **pull forward (MF-1)** |
| E3 ledger completeness + calibration | §4.2 | ✅ Aligned — **add materiality (R-1); pull forward (MF-1)** |
| E4 regression golden-set | §5.3 | ✅ Aligned |
| E5 G-Eval ×9 | §5.2 | ✅ Aligned |
| E6 prompt boundary + predicate bridge | §6.1, §6.3 | ✅ Aligned |
| E7 α/β behavioural matrix | §6.2 | ✅ Aligned — **split offline half (R-4); pin deps (MF-2)** |
| E8 DeepTeam adversarial | §5.4 | ✅ Aligned — **pin deps (MF-2)** |
| E9 context precision/recall | §4.3 | ✅ Aligned — **fix dependency naming (MF-2)** |
| — | §4.4 answer relevancy | ⚠ Dropped — record it (**R-6**) |

---

## Bottom line

Approve the approach and the ticket structure. Before locking: pull **E1–E3** forward as M3's independent verifier (**MF-1**), pin **`M2-T10` / showcase / Opus-for-impact** to canonical IDs (**MF-2**), add the **judge-reliability calibration** ticket (**R-2**), and give **E3 a materiality threshold** (**R-1**). The remaining items (R-3 through R-6) are one-line sharpenings. None of this changes the harness's shape — it tightens the sequencing so the integrity signals guard the change that most needs guarding, and keeps the ticket graph as traceable as the pipeline it tests.
