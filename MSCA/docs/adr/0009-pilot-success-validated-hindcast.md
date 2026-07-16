# Pilot success: validated hindcast counterfactual, feasibility with latency, user-acceptance

**Status:** accepted (2026-06-30)

**Context.** RQ7. ADR-0007 fixed the metric (decision-level economic calibration vs current practice), but a 1–2 season / few-site field pilot is underpowered to prove a real-field profit increase, and a naïve counterfactual (AquaCrop both recommends *and* scores) is circular.

**Decision — a pre-registered success ladder.**

1. **Primary — efficacy via a *validated hindcast counterfactual*.** Replay historical seasons over the pilot fields; score the method vs current practice on risk-adjusted profit / decision-regret (bootstrap CIs, λ-robust, per ADR-0007). Non-circular by construction:
   - **Outcome-model validation** — the AquaCrop model used to *score* outcomes is validated against observed yield/Brix (ADR-0006), so the ruler is independently trusted.
   - **Real-time information asymmetry** — both method and baseline decide using only information available *at decision time* (observations-to-date + forecasts), and are scored on *realised* outcomes. Any edge must come from better use of available information, not hindsight.
2. **Feasibility — field, with a concrete latency target.** End-to-end near-real-time operation on real fields, delivering a recommendation within a **pre-registered latency** (target ≤48 h from data availability / overpass ingest — exact number fixed in the plan). This is the "better timing" item, made falsifiable.
3. **Secondary / mechanism (reported co-benefits).** Per-operator calibration skill (RQ5); water savings at equal-or-better yield (WUE, reported not optimised — ADR-0003); stress-detection skill vs the fixed IRT.
4. **Light user-acceptance endpoint.** A lightweight usability / trust / actionability assessment with pilot users — **carries into RQ10** as a TRL-readiness signal.

**Honest scope + publishable null.** The pilot claims *efficacy (validated hindcast) + feasibility (field)*; a **population-level field-profit claim is future work** (mirrors RQ9). Pre-registered; "no uplift over current practice" is a publishable outcome.

## Consequences

- The AquaCrop **scoring/outcome model becomes a distinct validated artifact**, separate from the decision/recommendation model — and may need to be more rigorously validated than the decision-side model.
- Requires logging the **real-time information set at each historical decision point** (what was knowable when) — a data/design requirement on the hindcast.
- **RQ10 inherits** the user-acceptance endpoint as a TRL-readiness input.
