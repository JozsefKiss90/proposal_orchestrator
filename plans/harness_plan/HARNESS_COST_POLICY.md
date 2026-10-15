# Harness cost policy — subscription-covered track + single deferred paid ticket

> **Set 2026-07-21.** Operator constraint: no *separately-metered* paid service may be required to build, test, or run the harness. Claude LLM calls run on the **Claude Code subscription plan** (flat-rate — no per-call bill); the harness judge runs on a **local** (or otherwise non-drafter) OpenAI-compatible model at no added cost. Paid *external-framework* integration is deferred to a single ticket. Companion to `EVAL_HARNESS_TICKETS_REVIEW.md` / `EVAL_HARNESS_E3_PREAPPROVAL.md`.

## Policy

> Every harness feature must (a) unit-test with a fake/injected backend (zero network) **and** (b) run for real against a **non-drafter** OpenAI-compatible judge (a local model is the natural, no-added-cost choice). No feature may require a *separately-metered* provider to function, and no eval metric may ever gate a runtime DAG node. Anything that can only work by billing an external provider defers to **E10** (below).

Two invariants this rests on, both already enforced in code:

- **Never a runtime gate.** `judge.py`: "the judge never evaluates a gate and its output never fail-closes a run." Harness→runner is one-way (boundary test). Only the 138 deterministic predicates + byte-equal checks gate runs.
- **The added-cost line is the external framework, not the Claude calls.** The pipeline's Claude calls (drafting, composition, Opus-for-impact) run on the Claude Code subscription — flat-rate, no marginal charge. A local judge adds nothing. Only frameworks that call their *own* metered endpoints (DeepEval's cloud judge, Ragas embeddings, PromptFoo non-subscription providers, DeepTeam generation) bill separately → **E10**.

## Judge config (independent, no added cost)

The judge must be a **non-drafter** model over an **OpenAI-compatible** transport — `judge.py` rejects the drafter's `claude_cli` transport for grader–generator independence. So the judge does not ride the subscription's transport; point it at a local OpenAI-compatible server, which satisfies both independence **and** no added cost. It builds its backend from `resolve_provider_config()` (`ORCHESTRATOR_TRANSPORT_*`), overriding only the model with `HARNESS_JUDGE_MODEL`:

```
ORCHESTRATOR_TRANSPORT_PRESET=openai_compatible
ORCHESTRATOR_TRANSPORT_ENDPOINT=http://localhost:11434/v1   # Ollama / llama.cpp / vLLM / LM Studio
HARNESS_JUDGE_MODEL=<local-model-id>
HARNESS_JUDGE_VERSION=<pinned-tag>                           # a repin re-opens E1.5's advisory state
```

- The harness is out-of-band and never runs the pipeline, so this env is used **only** for harness commands — the pipeline keeps its own (Claude Code subscription) transport. Hold them in separate files (e.g. `.env.harness`).
- **Optional hardening (small E1-adjacent item):** give the judge its *own* transport vars (`HARNESS_JUDGE_ENDPOINT` / `_BACKEND`) instead of piggybacking `ORCHESTRATOR_TRANSPORT_*`, so it can never accidentally resolve to the pipeline's transport or a metered endpoint.
- **Judge-quality caveat:** a small local model is a noisier grader than a frontier Claude; it matters most for E1.5 calibration and the E3 materiality judge. A mid-size local model is usually fine as a non-drafter grader — pin it, and let E1.5 characterize it before graduating anything to gating.

## Free / paid taxonomy

**No LLM at all (pure deterministic — free anywhere):**

- E7a α-block (`gate_09` call), E4 baseline byte-diff, E3 lexical/ledger set-diff scaffolding, the E6 predicate bridge.
- **E9 core:** build the "relevant nodes per sub-section" gold set from vault front-matter (`upstream_nodes` / `downstream_nodes` / `source_refs`) → context precision/recall = set arithmetic on node IDs. No judge, no embeddings.

**No added cost — on the subscription + a local judge:**

- E2, E3, E1.5, status-calibration, E4 on real artifacts, the pre-E5 consolidation sweep.
- **Native rubric grader** = E5's substance (rubric-scored evaluator expectations) without DeepEval.

**Separately metered → deferred to E10:**

- DeepEval (E5 framework form), Ragas LLM-graded metrics (E9 framework form), PromptFoo provider/cost matrix (E6/E7), DeepTeam (E8; also run-dependent). These call their own paid endpoints.

## E10 — Paid / online framework integration (deferred)

Ready to paste into `tickets_eval_harness.md` at the next Rev:

```
## E10  Paid / online framework integration — DEFERRED (single ticket)
**What:** adopt the external frameworks whose value is inseparable from separately-metered calls —
DeepEval (G-Eval / DeepTeam), Ragas (LLM-graded context metrics), PromptFoo (provider/cost matrix).
**Gated by:** (a) an available budget, and (b) an online build session (satisfies the
API-currency guardrail — bindings can't be verified in the offline env). Never a runtime gate.
**Free cores already extracted to the native track (do NOT wait on E10):**
- E5 substance → native rubric grader (local judge).
- E9 substance → set-math context precision/recall over the front-matter gold set.
- E6 substance → native predicate bridge; E7a α-block is already deterministic.
- E8 substance → hand-authored adversarial fixtures + deterministic block assertions
  (the honesty invariants are checkable without DeepTeam's paid generation).
**Scope when funded:** framework bindings + provider/cost matrix + DeepTeam generation +
adversarial runs (behind M2-T10 / the showcase). One ticket, one budget line.
```

## Recommendation

Pull the free cores out of E5 / E6 / E9 into native tickets now — they need only the local judge or pure set math — and leave **E10** as the single, clearly-bounded paid deferral. Net: the entire integrity surface runs on the subscription + a local judge at no marginal cost, and budget/online gates only the *external tooling*, never the *capability*.

## Amendment 2026-10-14 (J0): one optional metered provider

> **Status: drafted, pending operator signature.** Decision record:
> `docs/tier4_orchestration_state/decision_log/harness-jev-j0-governance_2026-10-14.json`.
> Source: `plans/reports/jev_harness_overhaul_assessment_2026-10-13.md` §12, ticket J0.
> The policy above stays in force. This amendment adds one rule and retires E10's framework list.

**The rule.** A separately metered provider may be wired into the harness only when all of these hold:

1. **Optional.** It sits behind an injected backend. A missing key constructs nothing, every test runs
   against a fake backend with zero network, and the acceptance lane stays green without it.
2. **Never a gate.** Its outputs are advisory records. No value it returns reaches a freeze check,
   a criterion score, `weighted_total`, or any runtime DAG node.
3. **Capped.** Each run enforces a token budget and a request budget, and stops issuing new work when
   either is reached. Default caps are in the decision record (2M input tokens per run, $5 per month);
   the operator may change them there.
4. **Data-classed.** Only material whose data class permits that provider is sent. The classes are
   defined in the decision record and summarised below.
5. **Replayable.** Live responses are recorded and replayed byte for byte. A live call is not treated
   as reproducible.

The first provider admitted under this rule is TypeSafe Jev (`jev-1.13.0`, pinned id, never an alias).

**E10 is retired as a list.** DeepEval, Ragas, PromptFoo and DeepTeam are no longer separate
placeholders. Any of them, or another metered service, is admitted later under this same rule with its
own decision record. Their free cores stay on the native track as before.

### Data classes for external processors

| Class | Material | Claude subscription | Jev |
|---|---|---|---|
| D0 | Synthetic and pseudonymous fixtures (SYN-ALPHA, BIODIV-01 demo, MSCA-PF graph candidate, adversarial fixtures) | permitted | permitted now |
| D1 | Repository metadata (hashes, counts, ids, statuses) | permitted | permitted |
| D2 | The existing sanitised derivative, the ESR record, harness outputs quoting them | permitted | only after ZDR is confirmed in writing |
| D3 | The accepted anonymised derivative of the original | after its acceptance record | after acceptance **and** confirmed ZDR |
| D4 | The submitted original, its private configuration, graph root and register, the anonymisation mapping table, Table 1.4.1 as submitted, any unaccepted derivative, the Stage B candidate | not permitted (Bedrock inside the private network only) | never (J10 blocked) |

"ZDR confirmed" means written confirmation from TypeSafe that zero data retention is active on the
account in use, covering inputs and outputs, plus an executed DPA, recorded in a successor decision
record. A statement that ZDR is "available" does not satisfy it.
