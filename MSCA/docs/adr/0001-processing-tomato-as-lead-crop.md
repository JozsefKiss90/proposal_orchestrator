# Processing tomato as the lead crop

**Status:** accepted (2026-06-30)

**Context.** The methodology needs one concrete crop to calibrate AquaCrop, design ground-truth sampling, select a covarying patch, and populate the profit objective's value/cost terms — none of which can be done against an abstract "horticultural row crop." The source narrative named tomato only tentatively ("do I remember right, that it would be tomato first?").

**Decision.** Commit to **processing tomato** as the lead/reference crop for AquaCrop calibration and the field pilot, while continuing to frame the *method* as transferable to horticultural row crops — a generalisation claim, not a multi-crop calibration commitment.

**Why.** AquaCrop ships with FAO-validated tomato calibration, so we inherit a defensible parameterisation rather than building one. *Processing* tomato specifically grows in large, contiguous, mechanically-harvested, fully-irrigated fields, which (1) softens the sub-pixel problem, (2) gives the homogeneous-patch / control-stand route a realistic landscape to operate in, (3) yields a clean contracted price-per-tonne and known input costs for the profit objective, and (4) is a dominant irrigated row crop in the Hungarian / AgroVIR-like validation context the graph assumes.

## Considered options

- **Crop-agnostic ("horticultural row crops") for the pilot** — rejected: you cannot calibrate or validate against an abstract crop. Retained only as the generalisation/impact framing.
- **Fresh-market tomato** — rejected: smaller, fragmented, plasticulture/staggered plots worsen the sub-pixel problem and undermine the patch idea; volatile market prices muddy the cost ledger.
- **Other irrigated row crops (maize, pepper, onion)** — not chosen as lead; available as transferability examples.

## Consequences

- Sub-pixel severity sits at the milder end → strengthens the case that Sentinel-2 is workable and makes PlanetScope a "when-available" enhancement rather than a dependency (informs RQ8/RQ2).
- The profit objective (RQ6) can be built on contracted-tonnage economics.
- AquaCrop calibration targets a determinate processing cultivar (cleaner phenology) rather than indeterminate staked fresh-market tomato.
