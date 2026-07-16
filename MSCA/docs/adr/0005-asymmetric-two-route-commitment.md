# Asymmetric two-route commitment; Route B split into software + physical halves

**Status:** accepted (2026-06-30)

**Context.** RQ2. Both routes share one decision engine and produce the same latent state {root-zone soil water, canopy cover} with uncertainty; they differ only in how they extract it from a sub-pixel signal. We must decide how much of each to build — an MSCA fellowship cannot credibly build two full diagnostic pipelines.

**Decision.**

- **Route A — primary.** Fully built and validated; the **headline contribution** (probabilistic fusion diagnosis with explicit observation operators, per ADR-0002).
- **Route B — implemented, scoped, and sold as a *result-generator*** — a genuine A-vs-B comparison that yields a publishable result and an ecological-proxy contribution, **not merely a fallback**.
- **Route B splits into two halves with very different risk:**
  - **Software / analytical half — the natural patch proxy.** Use existing high-resolution soil/climate data to find a *naturally-occurring* homogeneous covarying patch, read it from the coarse pixel, infer the target crop's state. **In scope.** Risk is data-availability / analytical — modest.
  - **Physical half — the Control Stand Variant.** Deliberately plant a covarying species as a *designed* proxy sensor so covariation is measured, not assumed. **Conditional stretch, pending a secured field site.** Risk is agronomic / site / logistics / seasonal — high.
- **One shared decision engine** (AquaCrop → risk-adjusted profit) for both routes.

## Considered options

- **Strict co-equal both** — rejected: doubles the diagnostic build; Route A already "wants strong hands."
- **Route B primary** — rejected: centres the proposal on the unproven covariation assumption.
- **Route A only, Route B as paper fallback** — rejected: wastes the result-generating comparison and the distinctive Control-Stand novelty.

## Consequences

- **RQ9 (patch covariation validation) inherits the split + Control-Stand contingency:** the protocol needs a *baseline* form (natural patch, software half — always in scope) and a *stretch* form (designed control stand — only if a site is secured).
- **RQ4 (ground truth) inherits the Control-Stand contingency:** the sampling design branches on whether a physical control stand is planted (instrument the stand) vs natural-patch-only.
- The work plan presents **B as producing results**, strengthening the impact story without over-committing build effort.
