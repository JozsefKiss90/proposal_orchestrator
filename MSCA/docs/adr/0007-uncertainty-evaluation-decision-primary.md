# Uncertainty evaluation: four-level, decision-primary, pre-committed

**Status:** accepted (2026-06-30)

**Context.** RQ5 evaluates the methodology's "red thread." A single 90%-coverage check is insufficient: a model can pass it while being too wide, or while being miscalibrated at a specific operator. With only a few supersites (ADR-0006), calibration estimates themselves carry sampling uncertainty.

**Decision — a four-level evaluation with a pre-committed hierarchy.**

1. **Per-operator + end-to-end calibration.** Reliability diagrams / PIT histograms (+ coverage) at each operator — surface SM, root-zone soil water, canopy cover, AquaCrop-derived stress (vs fixed IRT), yield — *and* the retained AquaCrop calibration parameters (doi:10.1016/j.envsoft.2022.105556). **Diagnostic / localising role.**
2. **Proper scoring rules.** CRPS / log score, so sharpness is scored alongside calibration.
3. **Decision-level economic calibration — PRIMARY endpoint.** Decision regret vs an oracle; predicted-vs-realised profit distribution; cost–loss / value-of-information (probabilistic vs point estimate). This is where the red thread must prove itself.
4. **Baselines.** Deterministic point-estimate pipeline, two-step downscaling pipeline, **and a current-practice baseline** (calendar / soil-feel / standard scheduling).

**Small-sample fix.** Cross-validated calibration (leave-site-out / leave-season-out, robust to spatial/temporal autocorrelation) with **bootstrapped confidence bands** on every calibration and score estimate. No calibration claim is made without a CI.

**λ-sensitivity.** Decision-level results are tested across the plausible λ range from the contract-economics elicitation (ADR-0003); the recommendation must be robust to λ within its elicited uncertainty.

**Pre-committed metric hierarchy.** Fixed *before* seeing results, to avoid metric-shopping: **decision-level economic calibration rules** (primary); **per-operator calibration localises** (secondary/diagnostic).

## Why

Coverage alone is necessary but not sufficient; the decision level is where the thesis lives; few supersites demand bootstrap CIs; pre-commitment buys credibility; and the current-practice baseline is the benchmark that matters for impact.

## Consequences

- **RQ7 inherits** the current-practice baseline and the decision-level metric — pilot success is defined relative to beating current practice on decision-level economic calibration.
- Requires an autocorrelation-robust CV scheme (leave-site-out / leave-season-out), not naive k-fold.
- λ-sensitivity reinforces the contract-economics data requirement from ADR-0003.
