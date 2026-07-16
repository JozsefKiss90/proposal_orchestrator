# Sentinel-1/2 is the backbone; PlanetScope is an optional non-dependency enhancement

**Status:** accepted (2026-06-30)

**Context.** PlanetScope is the sparsest column in the literature — the *Real-Time Decision Support × PlanetScope* cell is the single explicit research GAP — but cost/access is a field-wide limitation, and access for this project is **not secured**. We must fix the dependency posture before designing the routes (RQ2).

**Decision.**

- **Backbone = Sentinel-1 + Sentinel-2** (Copernicus: free, access-guaranteed). The method must stand entirely on S1+S2. ADR-0001 supports this — processing tomato's large fields make S2's 10 m workable.
- **PlanetScope = an optional, when-available *spatial enhancement*** that sharpens the canopy observation operator for smaller / edge fields. It slots through the *same* observation operator as S2; the pipeline **never depends on it**.
- **Access route is named but unsecured:** ESA Network of Resources / Third-Party Missions sponsorship, or Planet's education-&-research programme. Presented as pursued-with-a-clean-fallback, not assumed.
- **GAP novelty is claimed conditionally** — the "full PlanetScope + radar + ground fusion for row-crop irrigation" contribution is asserted *only if* access lands.
- **Headline contribution stays sensor-agnostic:** "multi-sensor probabilistic diagnosis → economically-optimised irrigation," not "PlanetScope fusion."

**Why.** Staking the proposal on a commercial feed with real cost/access risk would be fragile; keeping novelty in the sensor-agnostic framework makes the contribution robust to the access outcome, while still letting us bank the GAP-cell novelty as upside.

## Consequences

- **Route A** treats PlanetScope as an optional higher-resolution covariate through the canopy operator, not a required input.
- **Data Access Risks** can downgrade PlanetScope from threat-to-feasibility to enhancement-at-risk.
- Every impact/novelty claim must have a **no-PlanetScope version** that still holds.
