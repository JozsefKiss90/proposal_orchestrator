# Strategic Positioning — MSCA Postdoctoral Fellowship

> **Tier 3 hand-lift (ticket 14).** Positioning against the MSCA-PF evaluation frame (Excellence 50% / Impact 30% / Implementation 20%; source: `section_schema_registry.json` MSCA-PF, HE MSCA evaluation form V.2.2) and the Part B-1 sub-section structure. Research positioning is vault-grounded; **career, training and host positioning are addressed against the operator-confirmed consortium** (see `decision_log/13b-real-data-consolidation_2026-07-16.json`) — a plant-physiology fellow hosted in a remote-sensing / geoinformatics group — with the ten research decisions and the Earth-observation / field-data providers confirmed.

## Differentiation within the MSCA-PF frame

MSCA-PF is a **single-researcher, single-beneficiary** action assessed on the researcher's development through an excellent, well-hosted research project — not a consortium research programme. This positioning note therefore separates the **research merit** (grounded in the methodology vault) from the **researcher-and-host merit** (1.3, 1.4, 2.1, 3.2), which rests on the confirmed pairing of a plant-physiology fellow (Cholakova) with a remote-sensing / geoinformatics host and supervisor (ELTE; Jung).

<<<<<<< Updated upstream
## Excellence (50%) — research and methodology *(vault-grounded)*
=======
MAESTRO is explicitly aligned with the call’s required maturity range (TRL 2–TRL 5). The project begins at TRL 2, focusing on the formulation and early experimental grounding of its core AI agent architectures and coordination mechanisms, and advances these to TRL 5 through integrated validation in operational environments across the selected Apply AI sector demonstrators.

### Positioning Against the Expected Outcomes
>>>>>>> Stashed changes

**1.1 Quality and pertinence of the R&I objectives; going beyond the state of the art.** The project targets the single empty cell of the reviewed literature's research-gap matrix — *Real-Time Decision Support × PlanetScope* (`[[Research Gap Matrix]]`, `source_grounded`) — and the underdeveloped combination of *learned multimodal fusion + explicit probabilistic crop-water-state + irrigation optimisation* (`[[Probabilistic Fusion Novelty Claim]]`). The defensible edge is the end-to-end coupling, argued narrowly and honestly, not "using satellites for irrigation." Objectives are measurable against a validation protocol (uncertainty calibration, decision quality) rather than asserted.

**1.2 Soundness of the methodology.** The distinctive methodological commitment is the **honest uncertainty chain** carried from observation to decision (`[[Uncertainty Chain]]`, `[[Uncertainty Aware AquaCrop Calibration]]`). The design is **risk-managed by construction**: two interchangeable diagnostic routes share one decision engine, so a rigorous-but-demanding route (Route A, `[[Route A - Direct Probabilistic Fusion]]`) is hedged by a lighter route that sidesteps the sub-pixel problem (Route B, `[[Route B - Homogeneous Patch Proxy]]`) — the analyst's own framing of "a two-route methodology with one shared decision engine" (RQ2). Open-science practices (open data/models, a DMP by month 6) and the gender/diversity dimension are required by sub-section 1.2 and are addressed at the methodology level; the concrete open-science and EDI plan is refined once the host's practices are known.

## Excellence (50%) — researcher & supervision

**1.3 Supervision, training, two-way transfer of knowledge.** The fellowship is hosted at **ELTE** (Budapest) under **Dr. András Jung** (Faculty of Informatics; Institute of Cartography and Geoinformatics) in **geoinformatics and remote sensing**. Supervision is structured around a **Career Development Plan prepared jointly by supervisor and fellow and submitted as a project deliverable at the start of the action (by months 2–3), then reviewed and updated at M12 and M24**, regular research reviews, and a genuine two-way transfer: the fellow brings **plant-physiology and non-destructive stress-phenotyping expertise** — the project's biological ground truth — into the host's geoinformatics group, and takes up the host's **remote-sensing, hyperspectral and multisensor-fusion** competences in return, evidenced by ≥2 methods seminars delivered at the host. Training also integrates the MSCA-PF mandatory transferable dimensions: **digital and AI skills** (including the responsible use of generative AI in environmental modelling and scientific coding), **knowledge valorisation and innovation/entrepreneurship** (translating the uncertainty-aware decision-support demonstrator toward user uptake), and **research integrity and open-science ethics** (FAIR data, open research software, reproducible validation).

**1.4 The researcher's professional experience.** **Dr. Rositsa Cholakova** (Maritsa Vegetable Crops Research Institute / Bulgarian Agricultural Academy, Plovdiv, Bulgaria) is a plant physiologist specialising in the **non-destructive evaluation of plant stress and crop monitoring**. Her PhD (*summa cum laude*, 2020) addressed the non-destructive evaluation of the physiological status of drought-stressed tomato plants (doi:10.2139/ssrn.5492527), with further peer-reviewed work on maize chilling-stress photosynthesis and biostimulants. That expertise is directly load-bearing for the project's ground-truth and validation protocol (RQ4). The Bulgaria → Hungary move satisfies the MSCA mobility rule and makes this a **European Fellowship**.

## Impact (30%)

**2.3 Scientific, societal and economic impact** *(vault-grounded).* Scientifically, the project would establish a defensible probabilistic-fusion decision framework where the literature is thin. Societally and economically, uncertainty-aware irrigation recommendation targets **water-use efficiency** (the confirmed decision objective, RQ6) and farm resilience for row-crop horticulture, with an ecological co-benefit in Route B's reliance on semi-natural covarying patches (`[[Route B - Homogeneous Patch Proxy]]`). Magnitude claims are kept proportionate to the **research-prototype TRL target (TRL 3–4, RQ10)**. Call-specific expected outcomes/impacts are governed by Tier 2B (Phase 1) and are not restated here.

**2.1 Career perspectives / employability.** The fellowship advances the fellow from postdoctoral researcher toward independent research leadership: a Career Development Plan submitted as a project deliverable at the start of the action (by months 2–3) and reviewed/updated at M12/M24; ≥3 peer-reviewed publications (≥2 first-author); ≥120 hours of transferable-skills training; co-supervision of ≥1 MSc thesis at the host; and a follow-on national or ERC-track proposal submitted within six months of the fellowship's end.

**2.2 Dissemination, exploitation and communication** *(partially vault-grounded).* The demonstrator-and-open-science posture supports the dissemination/exploitation logic (open research software, open validation data and protocol, peer-reviewed publication). Target groups are the host's geoinformatics / remote-sensing community and Hungarian tomato growers reached through the associated partner **AgroVIR** for farmer access and field feedback. IP arrangements remain to be detailed.

## Implementation (20%)

**3.1 Work plan, risk assessment, effort per WP** *(vault-grounded research content).* The work plan seed (`architecture_inputs/workpackage_seed.json`) organises the confirmed methodology into research work packages (diagnostic block, prognostic/decision engine, validation) plus the MSCA-structural training, communication and management packages. The risk assessment is lifted directly from the vault `[[Risk Register]]` (data access, validation, model complexity, operationalisation). Effort months run on the **24-month European Fellowship** timeline: Plovdiv → ELTE is an intra-EU move, hence an EF, and 24 months is the confirmed duration.

**3.2 Host capacity and hosting arrangements.** **ELTE** (Budapest, Hungary) — Faculty of Informatics, Institute of Cartography and Geoinformatics — hosts the fellowship, providing the **geoinformatics and remote-sensing** group's computing and geospatial infrastructure, supervision by **Dr. András Jung**, and access to Hungarian tomato field sites via the associated partner **AgroVIR**. Earth-observation data are secured (**PlanetScope** via the Planet platform/API; **Sentinel-1/2** open data) alongside **ERA5** meteorological reanalysis.

## Positioning summary

The **research** positioning claims only the novelty it can defend against the literature; the ten research decisions are now confirmed and tracked in `[[Ten Research Questions]]`. The **identity spine is operator-confirmed real data** — a plant-physiology fellow (Cholakova) hosted in a remote-sensing / geoinformatics group (ELTE; Jung), with AgroVIR providing Hungarian tomato field access and the Earth-observation providers (PlanetScope, Sentinel-1/2, ERA5) secured — recorded in `decision_log/13b-real-data-consolidation_2026-07-16.json`.

## Source grounding

Research positioning traces to the pinned methodology vault (`MSCA/methodology_graph/`, SHA `b4d9e57`); evaluation-frame facts trace to `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` (MSCA-PF). Consolidated per-fact provenance: `docs/tier3_project_instantiation/hand_lift_provenance.json`.
