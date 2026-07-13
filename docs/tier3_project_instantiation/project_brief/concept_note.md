# Uncertainty-aware multi-sensor diagnosis and economically optimised irrigation decision support for row crops

> **MSCA Postdoctoral Fellowship — Concept Note (Tier 3 hand-lift, ticket 14).**
> Lifted from the `source_grounded` methodology vault `MSCA/methodology_graph/` (pinned gitlink SHA `b4d9e57`, per `reinstantiation_provenance.json`). Provenance discipline: `source_grounded → Confirmed`, `synthesis → Inferred (framing)`, `inference → Inferred`, `unconfirmed → not lifted as fact` (Appendix B). Per-fact vault-node citations appear inline as `[[Vault Node]]` and are consolidated in `hand_lift_provenance.json`. **The identity spine (fellow / host / supervisor / partners) is Unresolved — see `call_binding/confirmation_checklist.json`.**

## Research problem *(Confirmed — `[[Core Architecture]]`, `[[Methodology Graph - Meta Node]]`)*

Irrigation decisions for row crops must be made under compounding uncertainty: the true state of the field, plant, soil and water is only partially observed, and the consequence of each irrigation choice depends on weather that has not yet happened. The project would **diagnose** crop/soil/water status from multiple uncertain data streams, use that diagnosis to **simulate** alternative irrigation decisions, and **recommend** the option with the best expected economic outcome. The problem decomposes into two scientific blocks — a **diagnostic branch** (the actual state of field, plant, soil and water) and a **prognostic branch** (given that state, what happens under each decision, so the best can be chosen) — tied together by **one chain that carries its uncertainty from end to end**. Keeping that uncertainty honest is the methodological heart of the work: every model output must report not only *what* the state is but *how sure* we are, and that uncertainty must travel all the way into the irrigation decision (`[[Uncertainty Chain]]`, `[[Uncertainty Propagation]]`).

## Scientific and technical approach

### The diagnostic branch — two routes, one shared decision engine *(framing: Inferred `[[Core Architecture]]`; routes: Confirmed)*

A single thread runs under **two interchangeable routes** to the diagnosed field state, both feeding the same downstream decision engine:

- **Route A — Direct Probabilistic Fusion** *(Confirmed — `[[Route A - Direct Probabilistic Fusion]]`, `source_grounded`)*: the rigorous one-step route. The satellite enters a **probabilistic machine-learning model** as one more covariate alongside radar (`[[Sentinel 1]]` SAR), optical (`[[Sentinel 2]]`; optionally high-resolution `[[PlanetScope]]`), weather, soil sensors and field observations, and the model goes straight to the field state with its uncertainty — one step instead of two, with no intermediate pixel to inflate the error (the `[[Downscaling Critique]]` of the `[[Sub Pixel Problem]]`). Candidate model families, all returning distributions rather than point estimates, are the `[[Bayesian Hierarchical Model]]`, the `[[Gaussian Process]]`, and probabilistic ML more broadly. The estimated latent state comprises `[[Root Zone Soil Moisture]]`, `[[Crop Water Stress]]`, canopy development, biomass and expected yield, each with an uncertainty range.
- **Route B — Homogeneous Patch Proxy** *(Confirmed — `[[Route B - Homogeneous Patch Proxy]]`, `source_grounded`)*: the lighter route that sidesteps the resolution problem by selecting a close, homogeneous patch — matched on high-resolution soil and climate data — whose biology covaries with the target crop and which the coarse pixel can read cleanly, with nothing to disaggregate. Its experimental extension deliberately plants a covarying species as a "designed proxy sensor" so covariation can be *measured* rather than *assumed* (`[[Control Stand Variant]]`).

> Whether both routes are implemented or one is the main method with the other a fallback/comparison is an **open project decision** (RQ2, `[[Route Comparison]]`), and the precise definition of the target field state is open (RQ3). Route B's central assumption — that the patch genuinely covaries with the target crop — **must be proven, not assumed** (RQ9, `[[Validation Risks]]`).

### The prognostic branch — decision under uncertainty *(Confirmed — `[[AquaCrop Decision Interface]]`, `[[Uncertainty Aware AquaCrop Calibration]]`)*

From the diagnosed state onward the path is the same for both routes. The state feeds the `[[AquaCrop Decision Interface]]`, which "stands for the plant" and is the interface through which decisions act, calibrated in an **uncertainty-aware** way that keeps an honest range rather than collapsing to one overconfident parameter set (building on the fellow-attributed method doi:10.1016/j.envsoft.2022.105556). The shared engine runs **counterfactual irrigation simulations** over weather ensembles and steers toward the best **expected profit** (`expected crop value − costs`), rather than yield alone (`[[Profit Based Objective Function]]`, `[[Expected Profit]]`, `[[Counterfactual Simulation]]`). The exact decision objective — profit, water-use efficiency, yield stability, drought-risk reduction, or a weighted combination — is an open project decision (RQ6).

## State of the art and novelty *(gap facts: Confirmed; novelty framing: Inferred)*

A systematic literature review (`[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]`) anchors the novelty argument in **Figure 6's research-gap matrix** (`[[Research Gap Matrix]]`, `source_grounded`): across 50 reviewed studies, counts fall sharply as sensor integration deepens and as the task shifts from detection to optimisation to real-time decision support; the two gradients meet in the single empty **GAP** cell — *Real-Time Decision Support × PlanetScope*. The defendable novelty *(Inferred framing — `[[Probabilistic Fusion Novelty Claim]]`, `synthesis`)* is that while multimodal `[[Data Fusion]]` is mature, **probabilistic, uncertainty-aware drought/irrigation frameworks for row crops remain underdeveloped**: few works couple *learned* multimodal fusion directly with *explicit probabilistic* crop-water-state outputs and irrigation optimisation end-to-end. Genuine probabilistic precedents exist and are respected (Bayesian Maximum Entropy drought fusion; copula-based drought↔irrigation scheduling; dynamic Bayesian networks; MF-FusionNet), but none combines all three. The claim is deliberately narrow — **"from multi-sensor observation to probabilistic diagnosis to economically optimised irrigation decision"** — and defensible only if the uncertainty chain is kept honest.

## Validation and the research demonstrator *(Confirmed hazards; TRL Unresolved)*

The tool is presented as a **standalone research demonstrator** (an MVP / `[[Web MVP and User Interface Layer]]`), not a product. Validation must establish a protocol that does not yet exist: what ground truth is collected (RQ4), how uncertainty calibration is judged — e.g. whether 90% prediction intervals contain the truth ~90% of the time (RQ5), what counts as pilot success (RQ7), and how patch covariation is proven (RQ9). The principal methodological risks are consolidated in the `[[Risk Register]]` (data access, validation, model complexity, operationalisation). The precise **TRL target** (research prototype vs validated MVP vs operational pilot) is an open project decision (RQ10).

## Open scientific decisions *(Confirmed as open — `[[Ten Research Questions]]`, `source_grounded`)*

Ten questions taken faithfully from the analyst synthesis (prompt.txt §10) must be answered to turn this two-route concept into a committed methodology: RQ1 crop (tomato *tentative* — default to "horticultural row crops"); RQ2 route scope; RQ3 target field state; RQ4–RQ5, RQ7, RQ9 the validation protocol; RQ6 the decision objective; RQ8 PlanetScope access; RQ10 the TRL target. These are recorded as open decisions, not resolved here.

## Unresolved identity spine (the honest block) *(all Unresolved — `[[Partner Roles Overview]]`)*

Consistent with the anti-fabrication discipline (CLAUDE.md §13.3), **no partner or person is invented**:

- **Fellow / lead researcher** — *Unresolved.* A PI Role is *inferred* from first-person authorship of the design narrative and ownership of the calibration method (doi:10.1016/j.envsoft.2022.105556), but the name and affiliation are unconfirmed, and whether that person is the PF fellow or the PF supervisor is itself open (`[[PI Role]]`).
- **Host / beneficiary organisation** — *Unresolved.* No host is named in any source.
- **Supervisor** — *Unresolved.* Not named.
- **ELTE (Eötvös Loránd University)** — *Unresolved; do not invent.* ELTE is **absent from all primary sources**; no role, contribution or affiliation can be derived, so the engine must never assert it (`[[ELTE Role]]`). Absence of evidence is not evidence against: if the team genuinely secures ELTE as host, the operator may confirm it or declare it via `working_assumptions.json`.
- **AgroVIR-type validation partner** — *Unresolved.* Appears only as "AgroVIR-like partners" assisting with feedback, farmer access, testing and validation — *not* owning or operating the tool; no committed partnership is stated (`[[AgroVIR Validation Partner Role]]`).
- **Validation farms / field sites, EO data providers, meteorological providers** — *Unresolved.* Implied by the methodology's infrastructure but none is named (`[[Unconfirmed Partner Placeholders]]`).

Each gap is enumerated with a confirmation action in `call_binding/confirmation_checklist.json`. Until an operator confirms a fact or β-declares a working assumption (`working_assumptions.json`, ticket 15), the spine remains Unresolved and the affected proposal sub-sections (Excellence 1.3/1.4, Impact 2.1, Implementation 3.2) cannot be finalised.

## Source grounding

All research claims above trace to the pinned methodology vault (`MSCA/methodology_graph/`, SHA `b4d9e57`). Primary sources cited by the vault: `[[Source - Methodology Idea]]` (PI first-person design narrative), `[[Source - Methodology Synthesis Prompt]]` (analyst synthesis, prompt.txt), `[[Source - Literature Review]]` (Report A gap matrix; Report B probabilistic-novelty precedents). Consolidated per-fact provenance: `docs/tier3_project_instantiation/hand_lift_provenance.json`.
