# Operator-aligned, depth-over-breadth ground-truth campaign

**Status:** accepted (2026-06-30)

**Context.** RQ4. ADR-0002 made the diagnosis a state-space with explicit observation operators, so validation must check *each operator*, not just the end-to-end output. The literature's standing weakness is the absence of dense ground-truth networks; an MSCA fellowship cannot build a regional one.

**Decision.**

- **Operator-aligned, layered ground truth** — measure each layer separately so every observation operator is independently checkable: surface soil moisture, root-zone soil water, canopy cover, derived yield/stress, and applied water.
- **Depth over breadth** — a few intensively-instrumented processing-tomato **supersites** (≈2–4 across a soil/irrigation gradient), plus a **light extensive tier** (yield + irrigation logs from cooperating farms) for external validity.
- **Keystone instrument: multi-depth soil-water profile stations** — top probe = surface SM, profile integral = root-zone storage; validates the surface→root-zone water-balance operator directly rather than assuming it.

**Per-supersite instrument stack:**

- Multi-depth soil-water profile probes (keystone).
- **Within-pixel probe replication** — multiple probes per satellite pixel; quantifies point-vs-pixel representativeness error *and* provides an empirical within-pixel covariation test (doubles as RQ9 evidence).
- Canopy: LAI / canopy-cover time series **+ periodic UAV** (sub-field heterogeneity, and a hedge against no-PlanetScope access — ADR-0004).
- **Fixed IRT (canopy temperature)** — *independent* validation of the AquaCrop-derived crop water stress. Thermal is a ground-truth check, **not** a model input; the sensor stack stays S1+S2 (ADR-0002).
- Biomass cuts + final yield **+ Brix / soluble-solids & grade** — feeds λ elicitation (ADR-0003), since processing-tomato contracts pay on quality.
- Irrigation logs + **actual applied water volumes**.
- Weather (on-site + ERA5-Land). Sap-flow **optional**.

**Timing: overpass-synchronised and phenology-stratified** — sampling timed to S1/S2 overpasses and stratified across phenological stages, so match-ups are temporally valid and span the crop cycle.

**Control-Stand branch (ADR-0005).** If a site is secured, the control stand becomes an added supersite with *paired* stand/target measurements (RQ9 stretch form); otherwise ground truth rests on natural patches + the target-crop supersites.

## Why

Independent per-operator validation is what makes the "honest uncertainty" claim credible rather than asserted. Depth-over-breadth addresses the dense-network gap within MSCA means, and each extra instrument pulls double duty (replication → representativeness *and* covariation; IRT → independent stress check; UAV → heterogeneity *and* PlanetScope hedge).

## Consequences

- **RQ5** inherits a clean calibration target: overpass-synchronised match-ups + within-pixel replication provide the repeated, distribution-characterising data that prediction-interval coverage needs; the surface→root-zone operator's error term is itself a calibration target.
- **RQ9** inherits an empirical covariation test: within-pixel replication measures covariation directly, so Route B's assumption is tested by the same design.
- Field-campaign cost is concentrated in a few sites — a schedule/staffing risk to track in the work plan.
