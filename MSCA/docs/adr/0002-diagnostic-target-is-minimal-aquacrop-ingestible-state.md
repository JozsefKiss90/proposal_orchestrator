# Diagnostic target is the minimal AquaCrop-ingestible latent state

**Status:** accepted (2026-06-30)

**Context.** The diagnostic branch could estimate any of soil moisture, crop water stress, canopy/biomass, yield risk, or "irrigation priority." Estimating "all of them" is unprincipled and would spawn parallel, redundant estimators that fracture the uncertainty chain.

**Decision.** The diagnostic target is the **minimal latent state that AquaCrop ingests** — exactly two state variables, estimated *with uncertainty*:

1. **root-zone soil water**, and
2. **canopy cover**.

Crop water stress, yield risk and irrigation priority are **derived outputs of AquaCrop**, not separate diagnostic targets.

## State-space discipline (the part that bites at RQ4/RQ5)

Latent state ≠ observations. The honest three-layer model is:

- **Latent state (target):** {root-zone soil water, canopy cover}
- **Observations:** {Sentinel-1 **surface** soil moisture (~top 5 cm), Sentinel-2 optical indices}
- **Observation operators (each carries its own error):**
  - surface soil moisture → root-zone soil water, via a **temporal water balance** (AquaCrop's own balance, or an exponential-filter / Soil Water Index step);
  - optical index → canopy cover, via a **conversion with its own error term**.

Two overstatements we explicitly reject:

- ❌ "Sentinel-1 measures root-zone soil water." S1 sees the **surface** (~5 cm); root-zone is *inferred* by the model and carries that inference's uncertainty.
- ❌ "NDVI *is* canopy cover." It is an observation operator with an error term, not an identity.

## Why

1. **Matches the sensor stack** — S1 SAR (surface moisture) + S2 optical (canopy), *no thermal band*, so stress is inferred, not measured.
2. **Single uncertainty chain** — one posterior over {root-zone soil water, canopy cover} propagates into AquaCrop, which emits uncertain stress/yield/profit. No second, parallel stress estimator to reconcile.
3. **Defensible scope** — "estimate exactly what the decision engine consumes" survives reviewer scrutiny; "estimate everything" invites "why those five?"

## Consequences

- **RQ4 (ground truth)** must validate at the right layer: measure *surface* soil moisture and *root-zone* soil water separately (plus canopy), so the surface→root-zone operator is checked, not assumed.
- **RQ5 (calibration)** evaluates uncertainty on the latent state *and* on the operators' error terms — the surface→root-zone water-balance step is itself a calibration target.
- **Route A** must represent observation operators explicitly, rather than regressing raw sensors straight onto stress.
