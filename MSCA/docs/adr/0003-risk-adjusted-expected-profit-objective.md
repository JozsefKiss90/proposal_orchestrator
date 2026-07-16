# Objective is risk-adjusted expected profit (single-objective)

**Status:** accepted (2026-06-30)

**Context.** The prognostic branch needs one scoring rule. Sources are emphatic — profit, not yield (`expected crop value − water − energy − input − operational cost`), averaged over the weather ensemble. Left open: pure vs weighted multi-objective, and risk-neutral vs risk-aware.

**Decision.** A **single objective**: maximise **risk-adjusted expected profit** — a concave utility of net profit (equivalently a mean−λ·risk / CVaR form), profit being `expected crop value − (water + energy + input + operational costs)` over the weather ensemble. Water-use efficiency, yield stability and drought-resilience are **reported co-benefits and constraints** (e.g. a water-allocation cap), **not terms in the objective**.

**Why risk-adjusted, not risk-neutral.** The risk-aversion is grounded in **decision-maker loss-aversion arising from contract-penalty asymmetry**: processing tomato is grown on delivery contracts whose payoff is asymmetric — falling short of contracted tonnage/quality is penalised more heavily than an equally-sized good year is rewarded — so the grower's utility over profit is genuinely concave. This is a *substantive economic* reason. We explicitly do **not** justify the risk-adjustment by the instrumental claim that "the propagated uncertainty would otherwise be inert."

**λ / utility curvature is elicited, not assumed.** The risk parameter (λ, or the curvature of *u*) is **identified from the contract economics** — penalty schedule, price/quality tiers, delivery thresholds — not set as a free hyperparameter. This makes the risk attitude empirical and defensible.

## Considered options

- **Weighted multi-objective (profit + WUE + stability)** — rejected: arbitrary weights are unfalsifiable and reviewer-bait. Stability/drought-resilience enter through the *risk attitude* on profit instead.
- **Risk-neutral expected profit** — rejected: ignores the contract-penalty asymmetry that actually governs the grower's decisions.

## Consequences

- **Contract terms become a data requirement:** calibrating λ needs real processing-tomato contract economics (penalties, tiers). The pilot must obtain these.
- **RQ7 (pilot success)** is scored against risk-adjusted expected profit (and regret vs the best option) — not raw yield or raw profit.
- WUE and water-cap compliance are reported and checked, but never traded off inside the objective.
