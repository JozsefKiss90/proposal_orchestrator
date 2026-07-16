# Covariation validation: incremental-information, claims-separated, publishable null

**Status:** accepted (2026-06-30)

**Context.** RQ9. Route B's load-bearing assumption is that a proxy patch covaries with the target crop; Validation Risks flags the real hazard as covariation that is weak or *context-specific*. Inherited: the baseline/stretch split (ADR-0005) and the within-pixel replication covariation test (ADR-0006).

**Decision.**

- **Covariation = uncertainty-aware information gain.** The claim is "conditioning on the patch *reduces the target latent state's predictive uncertainty*" (calibrated conditional predictive distribution), not a correlation coefficient.
- **Incremental-information confounder test.** The patch must add predictive information **beyond the model's existing inputs** (S1/S2, weather, soil) — conditional on the features Route A already uses. If existing inputs already explain the apparent covariation, the patch adds nothing. (Sharper than controlling for shared weather alone.)
- **Out-of-sample transferability, honestly scoped.** Leave-site-out / leave-season-out CV (autocorrelation-robust, per ADR-0007) establishes *within-sample* transferability only. **Population-level transferability is explicitly future work** — a few supersites cannot establish it.
- **Natural-patch and control-stand claims kept separate.** They carry different evidential strength — observational found patch vs designed, condition-controlled stand — and are reported as *separate* claims, never pooled.
- **Decision-level parity is the operational test.** Route B's decision-regret tracks Route A out-of-sample, both beating the current-practice baseline (ADR-0005 × ADR-0007).
- **Pre-registration incl. a publishable null.** The success criterion is fixed before looking; a negative result (no incremental information / no decision parity) is a **pre-committed publishable outcome**, not buried.

## Why

Incremental information is the honest confounder control; separating the two claims preserves evidential integrity; within-sample scoping avoids overclaiming generalisation from few sites; and the publishable null makes the test genuinely falsifiable while guarding against publication bias.

## Consequences

- The **natural-patch claim is evidentially weaker** (observational, few sites) than the **control-stand claim** (designed); the proposal must present each at its true strength.
- **Population transferability** becomes a named future-work item and an explicit limitation.
- Reinforces ADR-0007's pre-committed hierarchy and autocorrelation-robust CV scheme.
