# FIELDWISE — Part B1 scoring-improvement brief

**Date:** 8 September 2026  
**Purpose:** Answer bank and decision brief for a subsequent Part B1 revision; not rewritten proposal text.  
**Baseline:** Submitted proposal 101373105, sealed 7 September 2026; simulated ESR dated 8 September 2026.  
**Scope:** Part B1 only. No proposal files have been edited.

## 1. What should change the score

The strongest route is to make the existing scientific design assessable, then demonstrate that the people, field access and early workload can deliver it. Cosmetic corrections alone will not resolve the major weaknesses. Prioritise:

1. **The complete historical-spectrum → satellite-predictor → prospective-test chain**, including what happens when conversion fails.
2. **A dimensioned experiment, physiological outcome definition and analysis plan**, with independent replication and growth-stage handling.
3. **Evidence of supervision and credible delivery arrangements**, including primary supervision during ELTE blocks, archive access, field geometry, seasonal timing and resources.
4. **Quantified, bounded impact and communication**, separating direct project delivery, reachable users and later adoption.
5. Specific training, career, open-science and researcher-evidence improvements; then consistency corrections.

The ESR gives 3.6/3.7/3.5, or 72.2/100. Its finding-level deductions, aspect scores, 4.4 caps and “fundable ≥92” category are **simulation conventions**, not the Commission's scoring algorithm. Do not add action gains as if they were independently recoverable points. Official criterion weights make a 0.1 improvement worth 1.0 total point in Excellence, 0.6 in Impact and 0.4 in Implementation. The Seal of Excellence threshold is 85%; actual funding depends on ranking and available budget, not a universal 92-point cutoff. Sources: [evaluation form](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf), [official MSCA PF information](https://marie-sklodowska-curie-actions.ec.europa.eu/actions/postdoctoral-fellowships).

These are **arithmetic quality targets, not predicted outcomes**:

| Scenario | Excellence | Impact | Implementation | Weighted total | Interpretation |
|---|---:|---:|---:|---:|---|
| ESR baseline | 3.6 | 3.7 | 3.5 | 72.2 | Simulated assessment of the submitted version |
| Seal-level target | 4.3 | 4.3 | 4.1 | 85.2 | Requires substantive resolution of major gaps |
| Stronger revision target | 4.5 | 4.4 | 4.3 | 88.6 | Requires convincing evidence, not just fuller descriptions |
| High competitive target | 4.7 | 4.6 | 4.5 | 92.6 | Ambitious; no funding assurance |

The ESR's 87–88 projection includes actions outside this brief's scope. It cannot be carried over to a B1-only revision. Its claim that ≥92 is impossible within a day is also a planning judgement, not an established ceiling.

### How to use the answers

- **Supported:** directly stated in the submitted PDF or specifically identified supporting evidence. A statement in an earlier draft is not proof of a current commitment.
- **Proposed:** a concrete future design or delivery choice offered here. It can become a proposal commitment if feasible and adopted; it is not an accomplished fact.
- **Owner fact required:** unavailable or contradictory information that cannot honestly be supplied by drafting.
- **Fallback:** a defensible weaker route. Where it leaves a scoring weakness, that limitation is explicit.

Choose one coherent option per issue. Do not paste mutually exclusive options into B1. The detailed specifications below are working material; the later rewrite should compress them into the essentials identified in Section 5.

## 2. Answer bank

### R01. Specify what hyperspectral-to-Sentinel-2 transfer actually means

**Addresses:** F-01/F-03; W12; E2-a/c/f and archive detail in E2-b; A-20; OD-E5. **Priority:** highest. **B1:** §1.1 O1–O3 and §1.2 Stage 1/Stage 2, PDF pp.24–26.

**Preferred answer — a restricted, testable common-predictor chain.**

1. Audit instrument make/model, wavelength range, resolution, calibration records, measurement height/footprint, leaf versus canopy acquisition, plot dimensions, canopy cover, dates, treatments and matched physiology. Produce the year-by-variable coverage table. Neither an ELTE camera inventory nor an old MATE paper establishes which instrument generated the 2022–2026 archive.
2. Where calibrated canopy reflectance and wavelength coverage support it, calculate synthetic band reflectance as `R_band = integral(reflectance × spectral response) / integral(spectral response)`. Calculate indices **after** band integration. Use sensor-specific Copernicus spectral-response functions and record their version and the satellite processing baseline. Drop a band whose response lies outside the instrument range; do not invent SWIR values from a VNIR-only archive.
3. Treat white/dark-reference correction of proximal measurements separately from satellite atmospheric processing. Use Sentinel-2 Level-2A surface reflectance, cloud/shadow masks and recorded quality filters. Aggregate 10 m bands to a common 20 m analysis grid when using 20 m bands; interpolation to 10 m does not create independent 10 m information. Record view/illumination geometry; use a justified correction or restrict geometry and test sensitivity rather than asserting generic “BRDF correction”. The [Copernicus product documentation](https://sentiwiki.copernicus.eu/web/s2-products) describes Level-2A products; the [spectral-response library](https://sentiwiki.copernicus.eu/web/document-library) identifies the versioned response data.
4. Define an interior-pixel mask from the actual field polygons, edge buffer and crop cover. A **proposed** acceptance rule is ≥90% target-treatment coverage per pixel and at least four valid 20 m pixels per area on a matched date. Geometry, point-spread effects, geolocation and canopy cover must be checked; area alone does not prove purity.
5. Add proximal **canopy** spectra on selected prospective campaigns, matched to real Sentinel observations and physiology. Use the same frozen predictor definitions on both sensing routes. This estimates the within-field sensor discrepancy and compares historical versus commercial proximal performance. It supports a diagnostic separation of scale and environment effects; it does not prove an exact causal decomposition because effects can interact.
6. Report paired bias, RMSE, slope and prediction disagreement by band/index, season and stage. Define acceptable measurement discrepancy in relation to training variability and downstream decisions before the prospective test. One **candidate engineering screen**, requiring Jung/Hollós' judgement, is median absolute index discrepancy ≤0.25 historical standard deviations and ≤10% change in stress classifications on a locked sensitivity set. These are proposed tolerances, not literature-established universal thresholds.

**Alternative:** If the historical spectra are leaf-level, use a physically justified leaf-to-canopy model only where canopy structure, cover and acquisition metadata exist and the mapping can be checked independently before freeze. Otherwise restrict the transferable features. A radiative-transfer model name by itself does not resolve missing canopy information.

**Fallback:** If no credible spectral mapping can be established before freeze, retain a pre-specified soil-water/meteorological model as a **secondary operational baseline**, and classify the spectral route as an unresolved or failed transfer experiment. If paired prospective spectra cannot be funded, report the combined environment-plus-sensing transfer gap and remove any promise to identify the two components separately. Neither option closes the original satellite-transfer weakness fully; it narrows O2/O3 and the permitted MVP functions.

**Timing guard:** Prospective paired measurements may diagnose the frozen system, but may not tune its primary mapping. A sensor-mapping adjustment informed by either prospective season is a secondary adaptation. No claim that “harmonisation is validated before deployment” is justified without genuinely independent pre-deployment evidence.

**Owner facts required:** MATE archive specification and rights; Jung's technically feasible mapping and access to paired measurements; field polygons and crop cover; instrument/operator/time allocation. These are the remaining factual parts of OD-E5.

### R02. Dimension the experiment and define the physiological outcome

**Addresses:** F-02; W13; E1 phenology, experimental-unit and producer-compensation concerns; E2-b; A-21; OD-E6. **Priority:** highest. **B1:** §1.2, with resource and field implications in §3.1–3.2.

**Preferred answer — an explicitly proposed planning design, subject to field feasibility.**

| Element | Concrete design option | Interpretation/condition |
|---|---|---|
| Experimental structure | Three irrigation regimes × four spatial blocks = 12 separately managed treatment areas per season; randomise treatments within blocks | Water delivery must be independently controllable; adjacent pixels are not treatment replication |
| Treatment geometry | Candidate 80 × 80 m area per unit; 20 m inward buffer gives a nominal 40 × 40 m core | 0.64 ha per unit; 7.68 ha treatment footprint before extra access/isolation land. Grid alignment and crop purity must still be checked |
| Irrigation contrasts | Full crop-demand replacement; a proposed 60–70% replacement treatment; no supplemental irrigation after establishment, subject to crop-protection rules | Specify growth-stage windows, effective rainfall and rescue irrigation; “unirrigated” is not proof that stress occurred |
| Campaigns | Target 12 physiology campaigns per season, concentrated around canopy development, flowering/fruit set, fruit filling and ripening | Align a subset to clear satellite overpasses, ideally same day; log rain/irrigation between paired observations |
| Plant measurements | Five spatially distributed plants per treatment area per campaign; combine to an area-date reference | 720 plant-visits per season, 1,440 over two seasons; not 1,440 independent replicates |
| Analysis observations | At most 12 areas × 12 dates × 2 seasons = 288 area-date records before missingness | Repeated observations are clustered; using the same field twice gives temporal replication, not a second independent environment |
| Attrition planning | A 30% missing-pair scenario leaves approximately 202 area-date pairs | A sensitivity assumption, not a forecast or a power calculation |

The numbers above are **new proposed design parameters**, not descriptions of the existing field. Do not state that this design is available until the farmer and scientific team establish its physical and financial feasibility.

**Physiological reference:** Make stomatal conductance relative to stage- and campaign-matched well-watered controls the primary physiological axis; use leaf water status or another independently measured physiological endpoint to corroborate it where consistently available. Fluorescence provides complementary photochemical evidence, but normal Fv/Fm should not automatically classify a plant as unstressed. Record temperature/VPD, time of day, genotype, phenology and competing stressors. Irrigation treatment and AquaCrop provide context and comparators; using them as the outcome would make validation against the same environmental predictors partly circular.

**Concrete classification option:** Classify area-dates as physiological stress when conductance falls below a pre-specified lower control reference limit and the corroborating endpoint shows a concordant deviation beyond its repeatability limit. Classify ambiguous or confounded cases as indeterminate and report their frequency. Derive numerical reference limits from historical controls and measurement repeatability, without optimising them against model accuracy or prospective outcomes. Prespecify exactly how stage-matched controls are used to construct prospective labels; these are outcome measurements, not model inputs. Report a sensitivity analysis that includes indeterminate cases rather than making them disappear from denominators.

**Alternative:** If no common two-marker reference exists across the archive, use a single well-supported continuous physiological endpoint, with other markers as external corroboration. A classifier may then be a secondary analysis. Do not force a continuous regression or binary stress label onto incompatible historical measurements.

**Sample-size answer:** Request actual archive counts by year, unit, stage, irrigation regime and outcome, including missingness. Simulate interval precision and detection performance under the planned clustering and expected stress prevalence using historical variability. Pre-specify the minimum useful precision and the available sample-size ceiling. The proposed 12 areas do not establish adequate power; five archive years and two test seasons are particularly weak bases for broad between-year generalisation.

**Fallback:** Three blocks × three treatments = nine independent areas, with fewer repeated plant observations before sacrificing spatial replication, if precision analysis supports it. If only one area per regime is available, describe an observational feasibility study, not a replicated irrigation experiment. If the field cannot support valid satellite pixels, use a confirmed larger field or narrow the satellite claim; more plants do not cure mixed pixels.

**Owner facts required:** available hectares, irrigation isolation, field shape, cultivars, crop calendar, routine labour, maximum permitted stress, crop-loss arrangements, physiological measurement capacity and archive counts. These determine whether the preferred or alternative design is credible.

### R03. Name the model, validation, uncertainty and acceptance decisions

**Addresses:** F-02/F-03; E2-a; A-20/A-21; OD-E5/OD-E6. **Priority:** high. **B1:** §1.2 Stage 1; §1.1 measurability.

**Preferred answer:** Use a regularised logistic regression with a small, pre-specified predictor set as the interpretable probabilistic baseline; compare with a constrained gradient-boosted-tree classifier. Limit complexity according to effective independent sample size. Include stage or a defensible phenological covariate only where it is measured comparably and available at prediction time. Use simple agronomic comparators as well as an ML benchmark (R04).

Run outer leave-one-year-out validation across the five historical seasons. Imputation, scaling, feature selection, tuning and probability calibration must be fitted inside each outer training set, using year/group-aware inner splits. Select the final pipeline under a declared historical-data rule, refit using historical data only and freeze its configuration and model artefact. Separate model selection from claims about unbiased outer-fold performance.

Assess reliability curves, calibration slope/intercept and Brier score. If needed, use a low-complexity sigmoid calibration fitted on separate blocked predictions; use isotonic calibration only with enough independent calibration data. The [scikit-learn calibration documentation](https://scikit-learn.org/stable/modules/calibration.html) explains why calibration data must be independent of the base model's fitting data and why isotonic fitting can overfit small samples. Here, automatic random CV is inappropriate.

Use cluster-aware resampling or a hierarchical model for uncertainty; keep all observations from a treatment area together and report each prospective season separately. With very few year or block clusters, explicitly qualify interval stability. A stress probability is not itself an uncertainty interval. Out-of-domain or insufficient-quality observations should produce an abstention/limited-evidence flag, not a confident stress decision. Do not promise conformal coverage under untested domain shift.

**Proposed decision gates, to adopt or replace before fitting:**

| Gate | Proposed answer | If it fails |
|---|---|---|
| Scientific test complete | All scheduled opportunities logged; primary frozen-model results and uncertainty reported, including non-estimable metrics | A negative transfer result still fulfils the scientific reporting objective |
| Useful discrimination | Candidate balanced accuracy ≥0.70 and demonstrable advantage over a locked agronomic comparator | Keep model research-only; do not describe operational superiority |
| Probability usefulness | Positive Brier skill versus a frozen climatology/reference model, with calibration and uncertainty acceptable for the intended use | Recalibration is secondary; withhold calibrated-probability claims |
| Alert utility | Choose a threshold on historical predictions targeting sensitivity ≥0.80 with false-positive rate ≤0.20 | If no threshold meets both, prioritise sensitivity or specificity explicitly with the agronomist; do not hide the trade-off |
| Warning lead time | Compare timestamps of locked alerts with subsequent independently observed stress; report uncertainty caused by observation intervals | With sparse observations, report interval-bounded lead time or contemporaneous detection only |

These values are **candidate project utility thresholds**, not established tomato physiology standards. Report false-positive rate (`FP/(FP+TN)`) separately from the proportion of alerts that are false (`FP/(TP+FP)`). Merely crossing a point-estimate threshold with a wide interval does not justify deployment. Agree the required confidence/precision before model fitting; D1.2 records that decision rather than inventing it later.

**Alternative:** A Bayesian logistic or additive model can represent parameter uncertainty directly if Hollós can support it and sample size warrants the complexity. Select one primary model, not a catalogue.

**Fallback:** Retain the simple baseline, reduce predictors and omit the nonlinear model if data are too sparse. Report non-estimability when one stress class is absent. After both frozen-model seasons have been reported, evaluate a separately versioned recalibration; a season-1 adaptation tested on season 2 must remain secondary to the unchanged two-season primary analysis.

### R04. Answer the state-of-the-art weakness through comparators

**Addresses:** F-05; W14; A-23; OD-E17. **Priority:** medium, low factual dependency. **B1:** §1.1 positioning and §1.2 benchmarks.

**Preferred answer:** Position FIELDWISE against three existing approaches, explaining the additional evidence it will produce rather than claiming that prior work lacks physiology or ML altogether.

| Existing approach | What it already provides | FIELDWISE's testable addition |
|---|---|---|
| Thermal/CWSI measures | Temperature-based assessment of plant water stress | Check whether the proposed spectral/environmental workflow gives useful physiological agreement, calibration and warning information under a frozen prospective test |
| Soil-water/ET/AquaCrop scheduling | Crop-demand and water-balance estimates for management | Test whether independent physiology improves the identification of realised stress beyond imposed water deficit |
| ML-based tomato irrigation support | Existing data-driven predictions and management approaches | Evaluate unchanged temporal and sensing-scale transfer, uncertainty and limits to permitted operational use |

**References ready to use:**

- Alordzinu et al. (2021), *Rapid Estimation of Crop Water Stress Index on Tomato Growth*, Sensors 21, 5142, [doi:10.3390/s21155142](https://doi.org/10.3390/s21155142). Use as evidence that tomato CWSI assessment already exists; no FIELDWISE threshold is inferred from it.
- Martelli et al. (2025; online 20 December 2024), *Smart irrigation for management of processing tomato: a machine learning approach*, Irrigation Science 43, 1407–1424, [doi:10.1007/s00271-024-00993-9](https://doi.org/10.1007/s00271-024-00993-9). This is a direct comparator for processing-tomato ML irrigation work.
- Allen et al. (1998), [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/X0490E/X0490E00.htm), for ET-based crop-water calculations and growth-stage dependence. Retain the two existing Takács references for MATE's crop-specific foundation.

**Alternative:** Include CWSI as an empirical benchmark only if calibrated canopy-temperature, meteorological and wet/dry-reference measurements can be obtained consistently. Otherwise use it for positioning and compare empirically with the available soil-water or AquaCrop rule. Sentinel-2 has no thermal band; the model cannot produce a directly measured thermal CWSI from MSI alone.

**Fallback:** Replace generic novelty claims with a compact comparison using the existing MATE literature and FAO-56. Replace the bare EEA homepage with the exact indicator source if keeping the 30% statistic; otherwise remove that statistic and retain the evidenced water-management problem. A broad homepage is not adequate support.

### R05. Evidence the supervisors without inventing totals or commitments

**Addresses:** F-06; W16; E1's irrigation-supervision concern; A-18 and the B1-relevant evidence aim of A-19; OD-E4. **Priority:** highest among non-methodological Excellence actions. **B1:** §1.3, supported by §3.2.

**Supported evidence available now:**

| Person | Usable evidence | Limits |
|---|---|---|
| Tibor Janda | Repository CV dated 19 May 2025 records teaching *Plant physiological investigation methods I and II* (1997–2012), doctoral-school core membership from 2010 and council membership from 2013; research stays at CEA Saclay and Ben-Gurion University | Historical experience; not evidence of current FIELDWISE availability or total PhD/postdoctoral completions |
| Tibor Janda | A [2023 Széchenyi István University dissertation](https://wamdi.sze.hu/images/2024/Mutum_Lamnganbi_disszertacio_DOI.pdf), PDF p.2, names him as co-supervisor of Mutum Lamnganbi | Establishes a named doctoral-supervision example, not the defence outcome or a total completion count |
| András Jung | [ELTE's doctoral-programme page](https://terkep.elte.hu/en/content/doctoral-programmes.t.13072?m=4421) identifies him among its programme heads | Does not establish the number of researchers supervised |
| András Jung | [ELTE profile](https://terkep.elte.hu/en/content/dr-jung-andras.t.15182) lists relevant doctoral courses and research/teaching at Halle-Wittenberg, Leipzig and Ulm | Evidence of international experience; do not relabel all past appointments as current collaborations |
| Roland Hollós | B1 cites the 2026 GMD meta-modelling paper and assigns modelling, validation and uncertainty responsibilities | One output does not establish doctoral/postdoctoral supervision experience or available effort |
| Sándor Takács / Gábor Milics | B1 identifies the irrigation/AquaCrop and precision-agriculture contributions and cites Takács' tomato studies | Scientific expertise is evidenced; availability for protocol review and recurring advice is not |

Janda's source: [repository CV](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/docs/tier3_project_instantiation/source_materials/cv/JT_CV-HUN-2025-MGI-Janda-Tibor.pdf). The remaining baseline statements are from submitted B1 §1.3.

**Preferred answer:** Replace generic seniority claims with one compact evidence-to-task statement for each main supervisor. Add verified PhD and postdoctoral supervision totals, completed versus current, and one or two named international collaborations with role/output. State Janda's accountability for physiology and scientific gates; Jung's for sensor harmonisation; Hollós' for statistical design, calibration and leakage checks. Assign a named MATE agronomic review of the irrigation protocol before lock.

**Alternative:** Use the named documentary examples above where totals cannot be obtained. Evidence of one real supervision case is more useful than an unsupported impressive total. Describe international **experience** accurately when a current collaboration cannot be verified.

**Fallback:** Preserve the documented technical division and strengthen supervision delivery through R06. Label the track-record response partial. Do not substitute ATK's participation in an EU project for Janda's personal supervision record, and do not make the agronomic contributor responsible for approval without their agreement.

**Owner facts required:** supervision/completion totals, current collaboration roles, committed availability, who provides irrigation expertise if MATE cannot, and the named substitute for prolonged supervisor absence. No letter needs to be collected simply to restate a verifiable publication or historic appointment.

### R06. Turn training into timed activities and maintain supervision at ELTE

**Addresses:** F-07; W17; E2 career-skills observation; A-24; OD-E15. **Priority:** high. **B1:** §1.3 and §2.1.

**Preferred proposed training schedule:**

| Window | Activity/provider | Evidence of acquired competence | What remains unconfirmed |
|---|---|---|---|
| M1–M3 | Jung/ELTE: supervised module drawing on *Hyperspectral Imaging and Field Spectroscopy* and *Remote Sensing Methods and Technologies* | Reproducible band-convolution/QC notebook and sensor-transfer specification | Courses exist on Jung's ELTE profile; future timetable, fellowship access and individual supervision are not confirmed |
| M1–M3 | Janda/ATK + Takács/MATE: physiological reference and irrigation-design practical | Reviewed reference protocol, field randomisation and measurement repeatability exercise | Staff time and agronomic review role |
| M1–M3, with advanced follow-up M10–M12 | Hollós/ATK: blocked validation, calibration and uncertainty practical | Independently rerun historical folds and model-card review; later prospective diagnostics | Provider availability; this is a proposed bespoke module, not an advertised course |
| M4–M9 | Host research-support staff: reproducible research, FAIR data, responsible AI and IP | Versioned release package, DMP and rights map | Named service/contact and session date |
| M16–M21 | ELTE/fellow: paired sensing and transfer-diagnostics clinic | Sensor/environment comparison with limitations | Instrument and operator access |
| M22–M24 and M25–M30 | ATK support + AgroVIR: grant/valorisation clinic and FMIS evaluation | Proposal concept, evaluation protocol and dispositioned usability/interoperability findings | Support personnel and operational supervisor schedule |

Course evidence: [Jung's ELTE teaching profile](https://terkep.elte.hu/en/content/dr-jung-andras.t.15182).

**Supervision continuity:** Propose weekly 30-minute Janda–fellow meetings during M1–M3, a fortnightly joint physiology/EO/modelling session, and a joint sign-off before protocol lock and freeze. Specify ATK lab visits around measurement needs, access to the same versioned records at both institutions and one agreed deputy during extended absence. Thereafter retain the existing regular supervision, monthly written monitoring and quarterly CDP reviews. These are proposed arrangements, not confirmed calendars.

**Teaching:** Prefer two deliverable-backed teaching activities: an ATK/ELTE practical on physiological validation by M12 and an updated transfer-analysis practical by M24. MATE or Plovdiv guest teaching can substitute when scheduled; retain a host seminar/tutorial fallback if an external invitation does not materialise.

**Alternative:** Use assessed individual modules instead of promising enrolment in a future taught course whose timetable is unknown. Name provider, learning outcome, month and assessed artefact.

**Fallback:** Use open learning resources plus a documented supervisor review and teach through an existing host group meeting, subject to host scheduling. This improves specificity but does not establish unavailable specialist expertise. Do not make optional Plovdiv travel a core career dependency.

### R07. Demonstrate the fellow's readiness and correct the MSc claim in B1

**Addresses:** F-08/F-10; W18/W4; A-08/A-02 and the B1 evidence aim of A-29; OD-E2/OD-E18. **Priority:** medium. **B1:** §1.4.

**Preferred answer:** Build three short competence → evidence → project-task links:

- Physiology: published maize/chilling work and the documented fluorescence, stomatal and leaf-water measurement toolkit support independent outcome assessment. Do not relabel maize research as tomato irrigation research.
- EO transition: MATE COST PANGEOS STSM (10 days, 2025), MATE RGB/hyperspectral training (14 days, 2025) and ELTE geoinformatics/remote-sensing traineeship (three months, 2026) support preparedness for WP1/WP2. The submitted CV supplies these details; reusing relevant evidence in B1 does not require editing B2.
- Recent crop work: identify the 2025 watermelon proceedings contribution and the two 2026 manuscripts on tomato UAV evapotranspiration and proximal hyperspectral stress signatures as **under review**, not accepted publications. State the fellow's specific contribution only when confirmed.

For DrR, provide an existing version/date or commit hash, implemented functions, input/output types and one reproducible demonstration. Distinguish what runs now from FIELDWISE's planned probabilistic model, web functionality and validation. A dated private baseline record plus an in-text function summary is acceptable evidence where a public repository would conflict with background-IP strategy. Evaluators should not need to follow a link to understand the capability.

**MSc answer:** If an award is documented, use the degree and award date in B1. If it remains in progress, say studies in Environmental Engineering (2025–2026). If status cannot be established, omit the disputed credential from B1 rather than make a stronger claim. This is the B1 response only; CV-format repairs are out of scope.

**Alternative:** Replace unnamed AI/ML course lists with the already evidenced applied placements and a documented DrR function summary. Named certificates can be added if provider/title/year and completion are known.

**Fallback:** Describe DrR only as a pre-existing desktop research prototype and make assessed modelling training explicit. Neither a prototype nor an under-review manuscript proves an independently validated ML system. Retain fair treatment of the career break; it is not a deficit to explain away.

**Owner facts required:** degree status; actual training certificates; Kleffmann dates if used; manuscript contribution/status changes; DrR version, functions and permissions. These cannot be reconstructed from the ESR.

### R08. Quantify impact without inventing water savings or adoption

**Addresses:** F-11; W21; A-12/A-13; OD-E8. **Priority:** highest Impact action. **B1:** §2.3.

**Preferred answer — three distinct scales:**

1. **Direct delivery:** one development crop, one commercial environment over two seasons, one frozen model and transfer assessment, one web MVP and one external industrial evaluation. Add the actual validation hectares and achieved observation coverage when confirmed. If R02 is adopted, 7.68 ha is a proposed treatment footprint, not a secured site or a country-scale benefit.
2. **Reachable translation channel:** AgroVIR reported in August 2025 that its software served **over 700,000 hectares across Hungary and six other countries**. Attribute and date this company-reported figure. It evidences an established distribution context; it is neither FIELDWISE coverage nor an estimate of irrigated processing-tomato hectares. [AgroVIR source](https://www.agrovir.com/EN/insights-software.html).
3. **Longer-term eligible uptake:** ask AgroVIR for the subset of its network with relevant crop, irrigation, field-size/pixel and data conditions; report farms and hectares with denominator, date and definition. Then model uptake only as an explicit scenario, for example `eligible hectares × future adoption fraction`, after validation, integration and a later adoption decision. Do not multiply all 700,000 hectares by an assumed saving rate.

**Proposed evaluation reach:** target 6–10 growers/advisors and 2–3 FMIS/technical users for structured evaluation across contrasting farm sizes and digital literacy, plus a practitioner workshop target of 20 participants. These are recruitment targets requiring capacity agreement, not existing commitments or a representative survey. Assess completion of core tasks, correct interpretation of uncertainty, usability problems and integration effort. Do not equate attendance with adoption.

**Significance:** Quantify calibration/discrimination, false alerts, warning-time intervals and performance loss on transfer. Record irrigation volume, marketable yield and quality by treatment. This tests stress-monitoring value and water–yield relationships; because farmers are not randomised to DrR advice versus normal scheduling, it does **not** identify water savings caused by DrR.

Link the mechanism to the EU Water Resilience Strategy's efficiency and digitalisation aims, without adopting the EU's economy-wide 10% ambition as FIELDWISE's result target. [Commission strategy](https://commission.europa.eu/topics/environment/water-resilience-strategy_en). Link the fellowship itself to improved skills/employability, cross-sector experience, stronger knowledge exchange and research-to-teaching transfer, each evidenced by a training output, shared method or teaching activity. These correspond to the PF expected outcomes in the [2026–2027 work programme, pp.25–28](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2026-2027/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf).

**Alternative:** If AgroVIR cannot disclose crop-specific reach, use the dated public network figure only as context, alongside project-controlled targets. A sourced national processing-tomato area may be added, but do not substitute all tomato or all horticultural area for irrigated processing tomato. National-area figures were not established in this review.

**Fallback:** Use only direct delivery and modest recruitment targets that the fellow can support. Keep the no-promised-water-saving boundary. MVCRI remains a potential post-project extension route, not guaranteed multi-crop validation or a job offer.

### R09. Supply the communication plan the ESR asks for

**Addresses:** F-12; W20; A-14/A-15; OD-E9. **Priority:** high. **B1:** §2.2.

**Preferred proposed plan:**

| Audience | Main message | Channel/activity | Timing | Target and evidence |
|---|---|---|---|---|
| Growers/advisors | What an uncertainty-qualified stress alert means, when to inspect a crop, and when no advice is justified | Practitioner brief; demonstrations linked to AgroVIR evaluation; end-user workshop | Brief M12; demonstrations M25–M29; workshop M29–M30 | Two demonstrations and one workshop; target 20 workshop participants; attendance, questions and short comprehension feedback |
| Wider public | Why plants, satellites and uncertainty must be checked together before irrigation advice | Host web/news channels and accessible illustrated explainers | M3 project introduction, M12 field update, M24 results explainer | Three explainers; measured unique views where analytics permit; distinguish views from engaged readers |
| HU/BG students and practitioners | Which methods transfer and which require local validation | Hungarian/Bulgarian summary material and an open tutorial/seminar | M21–M24; reuse during M25–M30 | One reusable tutorial and two language summaries; participant feedback and downloads |
| FMIS/innovation audiences | What the validated MVP can and cannot support | Technical demonstration and integration briefing | M24 readiness; M27 review; M30 roadmap | One requirements-to-evidence record and one integration briefing; assessed issues, not promised sales |

Separate research dissemination (papers, scientific talks, data/code) from public communication and commercial exploitation. Name ATK, ELTE and AgroVIR channels as intended routes only after the relevant hosts agree to provide them. A proposed aggregate target of 300 measured views across the three public explainers is optional and should be adopted only if the channels provide a credible basis and analytics.

**Alternative:** Use one jointly hosted hybrid practitioner event with recorded demonstrations, rather than multiple travel-intensive events. Keep targets for meaningful feedback.

**Fallback:** A fellow-maintained public project page/repository, an online demonstration and a host seminar can supply channels under greater project control. Record actual reach if external-channel analytics are unavailable; do not claim a guaranteed audience. External article placement is a submission intention, not assured publication.

**Owner facts required:** host publishing access, named communication contact, AgroVIR recruitment support, language-production capacity, venue and event costs. Future event execution does not require a pre-submission letter.

### R10. Convert career skills into actions and reconcile CDP reviews

**Addresses:** F-13/F-14; W19; A-04/A-16/A-17/A-33; OD-E16. **Priority:** medium. **B1:** §1.3/§2.1/§3.1.

**Preferred answer:** Retain D5.1 at M3; conduct quarterly reviews at M6/M9/M12/M15/M18/M21/M24/M27/M30, with substantive transition reviews at the already named M12/M21/M24/M27 gates. There is no need to remove quarterly reviews merely to match the shorter table.

Propose three concrete independence measures: lead one cross-disciplinary methods clinic by M12; prepare a grant concept and mock-reviewed application by M21–M24; mentor a junior researcher/student through one reproducible data-analysis task between M10 and M21, if the host can assign a mentee. A grant **submission** can be the preferred outcome if a suitable call is open and the fellow is eligible; a complete reviewed application package is the fallback, not a promised award.

Use the existing PANGEOS contact base as a networking starting point, not a guaranteed active action throughout the fellowship. The [COST action page](https://www.cost.eu/actions/CA22136/) should be checked against the eventual project dates. If it has ended, follow the relevant successor community, conference working group or collaborator network without inventing membership. Record a presentation, shared method or follow-on concept as the outcome of networking.

**Alternative:** If no formal mentee can be allocated, lead a small peer-learning group and produce a reusable teaching practical. If no eligible grant call fits, obtain two external or host expert reviews of a complete proposal concept and resource plan.

**Fallback:** Retain the documented teaching history, deliver the host tutorial and use the existing publication/software outputs as evidence of progression. Do not claim co-supervision, a future grant scheme or a continuing Bulgarian appointment without evidence. Select an actual open scheme later against career stage and host eligibility; an ERC commitment cannot be inferred from holding a PhD.

### R11. Make open science and reuse concrete while protecting legitimate rights

**Addresses:** F-04/F-15; W15; E2-d; A-22/A-28; OD-E10/OD-E16. **Priority:** high relative to drafting effort. **B1:** §1.2/§2.2.

**Preferred proposed release plan:**

| Asset | Timing | Repository/licence option | If raw/background rights are restricted |
|---|---|---|---|
| Stress reference, sampling/analysis rules and freeze record | Protocol registered before fitting; final frozen version at M3 | Timestamped OSF registration; public protocol/metadata deposit in Zenodo, CC BY 4.0 | Publish the non-sensitive protocol and a dated description of any withheld element; do not register retrospectively |
| Model card and reproducibility package | Initial M3; archival release with the relevant research output | Version-controlled source repository plus Zenodo DOI; new separable research code under BSD-3-Clause, subject to actual ownership and dependencies | Share independently owned research components, documentation and test interfaces; do not promise rights in background DrR or contractor code |
| Harmonised archive | Data dictionary/availability map at M2; authorised release with first paper | Zenodo or an appropriate institutional repository; CC BY 4.0 where permitted | Metadata, access conditions, persistent catalogue record and synthetic examples; controlled access where authorised |
| Prospective dataset and transfer analysis | D2.1 M20; analysis/model-card update M21 | DOI-bearing deposit; non-identifying, rights-cleared data and analysis | Protect precise farm/customer identifiers; release authorised aggregation and reproducibility instructions |
| Research papers | Preprint on submission where permitted; required open access to publications | Relevant preprint server or institutional repository; appropriate OA route | Use a compliant repository/publication route rather than promise a commercial APC payment |
| Operational software and integration specification | M24 readiness; M30 roadmap | Separately versioned rights/access statement and documented interface | Keep the proprietary operational layer separate from the scientific evidence package |

Set a bounded internal disclosure review so “IP review” cannot indefinitely postpone every release. **A proposed 30-day review period is an institutional decision**, not an established FIELDWISE policy. Separate rights to analyse, share derived data, publish methods, release code and exploit commercially. FAIR does not mean every raw commercial record must be public.

Add a horticultural/irrigation audience by targeting *Irrigation Science* for an appropriate paper or a relevant ISHS irrigation/horticulture symposium whose dates fit the action. Keep EGU/ECPA as useful options. Replace a planned conference presentation if necessary rather than silently increase the travel budget.

**Alternative:** Use a single institutional repository providing timestamps, versioning and persistent identifiers, with links to source control. Equivalent infrastructure is sufficient; brand names are not the objective.

**Fallback:** Commit firmly to the protocol, model card, non-sensitive metadata and separable research code the beneficiary can legitimately release. State exact restrictions for the archive and operational layer. Synthetic data are useful for software reproducibility but do not reproduce biological validation. DMP, licences and access contracts can be finalised after submission before the relevant use/release; the intended open-science approach must already be assessable in B1.

### R12. Replace the “missing letters” framing with credible dependency management

**Addresses:** F-16; W24; A-26; OD-E11; overlaps R02/R15/R17. **Priority:** highest Implementation dependency. **B1:** §3.2, supported by §3.1.

**Rule:** The 2026 PF template confines the mandatory commitment letter to the outgoing host of a **Global** Fellowship and notes that the non-academic-placement letter is no longer required. FIELDWISE is a European Fellowship. Do not create a pre-submission signature exercise for ELTE, AgroVIR, MATE, the farmer or Krumatic as if their letters were eligibility documents. However, an evaluator may still find an unsupported critical dependency unconvincing. [Official 2026 template, version history and §9](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/af/af_he-msca-pf_en.pdf).

| Dependency | Preferred B1 answer | Agreement can follow submission | Alternative/fallback and scoring limit |
|---|---|---|---|
| MATE archive | State the actual custodian, accessible years/variables, permitted analysis and evidence of availability; distinguish analysis from redistribution/commercial reuse | Execute necessary data-use terms before the first analysis, ideally before funded M1 given the M3 freeze | Use a confirmed legally accessible common subset. If the whole archive is inaccessible, O1/O2 require redesign; a generic backup promise does not close this major gap |
| Commercial producer | Identify the organisation or specific site description; state usable area, separate irrigation control, two-season availability, crop-management responsibilities and compensation/resource arrangement | Finalise site-use, crop-loss and operational terms before interventions and the relevant planting commitment | Use an identified, geometrically suitable comparable site. If none is established, identify the unresolved dependency; do not call a candidate site secured |
| Krumatic | State deliverable-based engineering scope, source delivery, interfaces, ownership/access, commissioning responsibility and funding source | Contract before paid development or code/data access requiring it; prototype provenance can be recorded earlier | Procure another qualified provider or use a leaner host-supported implementation with demonstrable capacity. The fellow cannot absorb unbudgeted full-stack work by assertion |
| ELTE | State secondment blocks, scientific tasks, supervisory continuity and the specific access required for those tasks | Complete detailed access/secondment arrangements before M1 activities that depend on them | Book a reduced instrument programme or a confirmed equivalent shared facility; core EO expertise remains necessary |
| AgroVIR | State requirements, placement tasks, operational supervision and test-data route; proprietary customer data are already explicitly not a dependency | Finalise placement operations and access before protected-data use/placement; the placement role must be clear in the proposal | Use approved synthetic/coded test data for interoperability. A replacement company requires a real arrangement and appropriate grant approval; it cannot be assumed to preserve the placement automatically |
| MVCRI | Preserve the optional post-MSCA route and named research connection | Future collaboration details can follow the project result and later funding | Generalise the route to future crop-specific research if no institutional commitment exists; no core in-action validation depends on MVCRI |

**Status vocabulary:** “Agreed in principle” requires an actual agreement in principle; “contract to be executed before analysis” is a future condition; “confirmed access” requires actual evidence. Evidence may be an existing authorised arrangement or correspondence rather than a newly signed letter. Do not turn the absence of a document in the reviewed files into a claim that no real agreement exists.

**Preferred fallback where paperwork is pending but participation is real:** State the known role/capability, the specific execution deadline, the responsible owner and the fallback. Explain how analysis/development proceeds only once necessary rights are in place. This can improve credibility without pretending the contract is signed.

**Irreducible gaps:** A missing letter is not intrinsically scored; an unknown field or inaccessible training archive remains a major scientific feasibility problem. Formal participant status is not a universal cure: a contractor can remain a contractor and MVCRI is not a core delivery partner. The ESR's “four informal organisations” count must not be repeated as if all four threaten O1–O3 equally.

### R13. Make the seasonal calendar and first-quarter effort believable

**Addresses:** F-17/F-18; W9/W10/W11; A-09/A-11/A-34; OD-E7. **Priority:** highest. **B1:** §1.1 feasibility and §3.1.

**Preferred proposed calendar:** A February start aligns an M3 freeze in April, first principal field observations from May, and the second autumn harvest by M20, assuming the producer confirms the local cultivar/harvest schedule. For illustration, **February 2028** gives M3 April 2028, M4 May 2028, M8 September 2028, M16 May 2029, M20 September 2029 and M21 October 2029. This is a calendar design option, not an agreed start date; the eventual grant's allowed start window must accommodate it.

**Alternative:** A March start can work if an end-May M3 freeze demonstrably precedes any prospective outcome used for the test and the actual transplanting/sampling window. A start month alone is insufficient: give the within-month freeze-to-first-observation order. Do not select a January start mechanically; a September second harvest would fall in M21 unless the crop can genuinely be harvested earlier.

**Slipped-start fallback:** Select the next feasible start within the permitted grant window before the action begins. Once running, a comparable backup site may protect access but cannot move the Hungarian growing season. If two full independent prospective seasons cannot fit, either obtain a feasible rephasing of the action or state the narrower one-season evidence scope and resulting limitation. Do not relabel a retrospective season, greenhouse cycle or crop from a different climate as the unchanged primary test.

**First-quarter feasibility answer:**

- M1: archive intake/QC, geometry/access checks and physiological definition; host support handles rights, contracts and administrative preparation; ELTE supports sensor specification. Existing relationships and completed training can evidence readiness, but not a completed archive audit.
- M2: complete the archive/coverage map, settle common predictors and locked protocol, run the reproducible pipeline on historical data; limit early software work to architecture/interfaces.
- M3: finish blocked model evaluation and freeze; verify field readiness; complete the CDP and initial dissemination plan. Defer advanced training, public-event production and non-critical interface polish to later months.

The original five WP totals can be retained, but the fellow's pre-freeze WP1 effort cannot be three full PM **plus** time on WP2/WP3/WP5. The following **proposed allocation option** preserves every WP total and stays within the fellow's capacity in each period:

| Fellow effort, PM | M1–M3 | M4–M9 | M10–M12 | M13–M15 | M16–M21 | M22–M24 | M25–M30 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WP1 | 2.2 | 0 | 0.6 | 0 | 2.2 | 0 | 0 | 5.0 |
| WP2 | 0.3 | 4.2 | 0.3 | 0.6 | 3.6 | 0 | 0 | 9.0 |
| WP3 | 0.2 | 1.2 | 1.4 | 1.3 | 0.1 | 1.8 | 0 | 6.0 |
| WP4 | 0 | 0 | 0 | 0 | 0 | 0 | 5.4 | 5.4 |
| WP5 | 0.3 | 0.6 | 0.7 | 1.1 | 0.1 | 1.2 | 0.6 | 4.6 |
| **Period total** | **3.0** | **6.0** | **3.0** | **3.0** | **6.0** | **3.0** | **6.0** | **30.0** |

WP1's remaining 2.8 PM are explicitly later transfer diagnostics and specification work, not concealed extra pre-freeze modelling. This allocation demonstrates arithmetic feasibility, not proof that the early modelling fits 2.2 PM or that every monthly peak is manageable. It protects field seasons and shifts most standalone training/communication and software work away from M16–M21; embedded technical training remains counted within the research tasks. Host/ELTE/MATE support must specify tasks and availability outside fellow PM. Before adoption, resolve the within-period monthly peaks and staff-supported campaign days; maintain 24 fellow PM plus six placement PM and count embedded training once. The matrix belongs in the working revision record; B1 needs only its convincing effort rationale, not necessarily another large table.

**Alternative with more early model time:** Move freeze to early M4 only if the real planting/observation calendar still leaves the complete primary prospective test untouched. Reconcile T1.2/T1.3, protocol/model deliverables, MS1, field launch and all corresponding B1 statements and Gantt marks. Keep the CDP at M3 unless its own rationale changes; moving the scientific gate does not automatically require moving D5.1. If the first ELTE block is extended, reduce a later block so the total remains 12 months.

**Fallback:** Keep M3 but select fewer defensible predictors and one simple model. If the data-readiness and support assumptions are not true, acknowledge the remaining feasibility weakness; saying that “tasks run in parallel” does not resolve one person's workload. Protect the actual freeze-before-outcomes principle even if a date changes.

### R14. Describe hosting through the resources the fellow will actually use

**Addresses:** F-20; W23; E2-e; A-25; OD-E12. **Priority:** medium. **B1:** §3.2.

**Preferred proposed answer:** Describe the ATK home team and primary supervisor; workspace and laboratory induction in M1; a workstation and secure project storage with versioned backup; access to required plant-physiology equipment; who handles employment/onboarding, reimbursement, data/IP issues and grants support; and integration into group seminars and supervision while at ELTE. Specify how EO processing and data access continue during ATK months rather than listing facilities at ELTE alone.

A proportionate **planning specification**, to be checked against actual jobs, is a CPU workstation with roughly 32–64 GB RAM and 1–2 TB active project storage, remote/queued institutional processing for larger EO tasks, and backed-up institutional storage for records. This is not an existing ATK allocation or a purchasing requirement. Limit stored imagery to the required sites/dates; the proposed simple models do not intrinsically require a GPU. Give the actual provision if different.

**Alternative:** ELTE hosts the EO environment with agreed remote access throughout ATK months, while ATK provides physiology, secure shared records and employment support. Name how access and support persist beyond physical secondment blocks.

**Fallback:** Specify only verified facilities and a realistic provisioning deadline before first use. A host gender-equality-plan statement is not an answer to absent compute or onboarding detail. Do not promise housing, childcare, relocation payments, particular licences or equipment without host evidence. Family/relocation support can be described as access to information or assistance if that is what the host actually provides.

**Owner facts required:** current hosting unit, HR arrangement, contract provision, equipment slots, workstation/storage access, technical contact, remote access and support service. The contract may be executed after submission; the proposal should contain a credible hosting plan.

### R15. Link necessary resources to a feasible delivery scope

**Addresses:** F-22; W8; E1 crop-loss compensation; A-27; OD-E13. **Priority:** medium; higher if paid engineering or the field is unsecured. **B1:** §3.1–3.2.

**Preferred answer:** Add a compact resource-to-source statement, not a new Part A budget. The ESR identifies €30,000 in research/training/networking contributions over 30 months; this does not establish that the entire sum is uncommitted or available for software. Obtain the host's actual allocation and identify existing access versus new expenditure.

| Essential resource | Required answer | Lean alternative/fallback |
|---|---|---|
| Irrigation monitoring, weather/soil sensors and maintenance | Equipment already available or specified procurement/loan; installation/operator responsibility and source | Existing calibrated kit, shared station where representative, manual checks; do not replace treatment-specific soil data with an unrepresentative remote station |
| Physiological and paired spectral measurements | Instrument, operator, campaign time and transport allocation | Fewer matched campaigns and simpler methods, retaining the independent reference and honest transfer claims |
| Producer burden/crop loss | Who supplies irrigation, routine labour, treatment isolation and any compensation, under the host-approved arrangement | Agree a smaller scientifically valid footprint or supported site; unpaid contribution cannot be presumed |
| Engineering | A scoped specification and quotation/capped work package; commissioning source, source-code delivery and maintenance boundary | Thin web MVP with ingestion, provenance, frozen inference and uncertainty display; defer polished dashboards/production FMIS integration |
| Publications, events and training | Source for travel, fees and event delivery | Repository OA/appropriate no-APC routes, one combined event and online participation |
| Compute/storage | Existing institutional provision or explicit approved allocation | CPU-first, small-area EO processing and use of existing infrastructure |

**Alternative:** Stage commissioning after archive/design readiness and fix a minimum operational scope. Pay for optional UAV acquisition only after the core physiological and satellite measurements are secured.

**Fallback:** Reduce optional features, extra travel and supplementary UAV use before cutting independent field replication or reference measurements. Do not assume host co-funding, free partner engineering or a loan of instruments. If the essential scope cannot be financed, the feasibility gap remains; do not invent quotations to make the arithmetic balance.

### R16. Resolve numbering without creating work

**Addresses:** F-23; W5; A-03; OD-E20. **Priority:** low. **B1:** all deliverable references and Gantt.

**Preferred answer:** Renumber the existing model/card D1.4 → D1.3 and transfer specification D1.5 → D1.4 consistently. No new scientific deliverable is required merely because a number is missing. Check §1.1, §1.2, §2.1, §2.2, WP1, milestones and the Gantt together.

**Alternative/fallback:** Keep the original numbering everywhere if the diagram cannot be safely regenerated. A consistent gap has much lower scoring importance than an incorrect model-freeze date or broken cross-reference. Do not infer that an absent D1.3 proves omitted scientific work.

**Open decision:** The later editor should establish whether the chart source reproduces the submitted diagram. This brief does not modify or regenerate it.

### R17. Make risk responses decision-specific

**Addresses:** F-21; W22; A-10; access/availability parts of OD-E11–OD-E13. **Priority:** medium. **B1:** §3.1 risk table.

**Preferred proposed risk changes:** Integrate missing dependencies into the existing six rows where possible. Adding one generic “partner failure” row without distinct consequences will not resolve the weakness.

| Risk and check point | Trigger | Response | Owner |
|---|---|---|---|
| Archive rights/coverage at intake | No permitted access before analysis, or common variables insufficient at M1 audit | Activate a specifically identified permitted subset; reduce features; escalate redesign if core archive absent | ATK + fellow + MATE custodian |
| Field/irrigation/calendar before planting | Site geometry, irrigation separation or two-season access unavailable by readiness decision | Activate an identified comparable site before crop window; otherwise change evidence scope and schedule explicitly | ATK + fellow + producer |
| Model freeze | The locked pipeline cannot be reproduced by the planned date | Reduce complexity before deployment; use only an already specified baseline; no fitting to prospective outcomes | Fellow + Hollós + Janda |
| Sensors/satellite availability | Failed calibration, insufficient interior coverage or too few matched dates | Spares/manual reference checks, logged missingness and limited claims; UAV remains supplementary | Fellow + ELTE + producer |
| Supervisor/ELTE access | Prolonged absence or critical review/access missed | Pre-agreed deputy and remote joint review; substitute facility only where genuinely equivalent and available | ATK + ELTE |
| Engineering/AgroVIR | Critical tests missed, source rights unresolved or placement availability withdrawn | Narrow MVP, use a qualified replacement provider if secured; protect scientific deliverables; resolve placement change explicitly | ATK + Krumatic/AgroVIR |

**Likelihood/impact answer:** Ratings should reflect exposure and evidence, not be diversified cosmetically. Before agreements, archive/field risks may be M/H; cloud loss may be H/M if gaps are frequent but bounded; complete loss of satellite evidence remains H impact. After confirmed access, likelihood may fall while impact stays high. These are assessment examples for the owners, not established FIELDWISE probabilities.

**Alternative:** Keep the original six-row form but add the appropriate rights, field and availability triggers to R1/R2/R4/R6 and specify a deputy elsewhere. This may be more space-efficient than a seventh row.

**Fallback:** Retain honest identical ratings where justified and improve the triggers/decision consequences. A fallback is not “switch site” unless a suitable site exists, and is not “recalibrate” unless the primary frozen result remains separately reported.

## 3. Host, partner and supervisor claims that remain unresolved

The following are **scoring-relevant facts or commitments**, not a demand for new letters. They should be resolved before the later writer states them as facts. Operational documents can follow submission at the times in R12.

| Owner | Exact missing answer | Use in B1 | Safe response if unavailable |
|---|---|---|---|
| MATE / Takács | Instrument and footprint; spectral range; per-year units/campaigns; common physiological variables; analysis and reuse permissions | R01–R03/R12; §1.2/§3.2 | Acknowledge missing archive specification; limit the common-variable claim; do not assert full harmonisation feasibility |
| Farmer + ATK | Identity/site description, polygons/area, irrigation control, two-season crop calendar, routine labour, compensation and genuine backup site | R02/R12/R13/R15 | Present a proposed design and unresolved site fit; no “secured site” wording |
| Jung / ELTE | Paired-spectrum access, measurement/operator time, technical transfer route, course access, remote computing, continuity/deputy | R01/R05/R06/R14 | Use published expertise/course facts; restrict claims of allocated access |
| Janda / ATK | Supervision totals, current collaborations, primary-supervision time, irrigation adviser and deputy | R05/R06 | Use the sourced supervision example, CV evidence and a clearly proposed routine |
| Hollós / ATK | Available time, model/calibration method, statistical support, any supervision track record | R03/R05/R06/R13 | Retain documented technical role; no invented supervision total |
| ATK support services | Workspace, equipment slots, compute/storage, onboarding, HR/support contacts and resources | R14/R15 | Describe verified provision and a deadline for provisioning; no unsupported welfare benefits |
| Krumatic + ATK | Scope/quotation, commissioning source, source delivery, licences, delivery capacity | R12/R15 | Leaner specified MVP or verified alternative provider; no free engineering assumption |
| AgroVIR | Relevant crop-specific network subset, evaluation participants, channel access, staff time, placement routine | R08/R09/R12 | Dated public overall footprint plus proposed, bounded recruitment; synthetic/coded testing where appropriate |
| MVCRI | Actual post-project research/teaching opportunity and support | R08/R10/R12 | Potential continuation route only; no promised employment or multi-crop results |
| Fellow | MSc status, DrR functions/version, training completion, contribution to manuscripts | R07 | Use documented evidence; omit disputed credential and avoid mature-software claims |

The August operator/review packs contain useful leads but also superseded host/supervisor arrangements and candidate facilities. They were not used to override the sealed September B1. In particular, a public equipment list or a previous professional relationship is not an allocation of equipment or land to FIELDWISE.

## 4. Coverage of the ESR, watchlist and owner decisions

### Findings and revision actions

| ESR finding | Response | Watchlist | ESR actions supported | Treatment |
|---|---|---|---|---|
| F-01 | R01 | W12 | A-20 | Core scientific specification |
| F-02 | R02/R03 | W13 | A-21 | Includes phenology, reference, replication, power/precision and preregistration |
| F-03 | R01/R03 | — | A-20 | Model/UQ/calibration and paired prospective spectra |
| F-04 | R11 | W15 | A-22 | Open science; preserve justified gender-content statement |
| F-05 | R04 | W14 | A-23 | Comparator positioning and usable references |
| F-06 | R05/R06 | W16 | A-18; B1 evidence purpose of A-19 | No B2 editing; do not rely on A-07 as the B1 solution |
| F-07 | R06 | W17 | A-24 | Specific training and primary-supervision continuity |
| F-08 | R07 | W18 | A-08; B1 evidence purpose of A-29 | Readiness, outputs and prototype |
| F-09 | Excluded | W2 | A-05 excluded | B2 CV-format issue; do not book a gain from it |
| F-10 | R07 | W4 | A-02, B1 only | Degree-status inconsistency |
| F-11 | R08 | W21 | A-12/A-13 | Magnitude and call/policy relevance |
| F-12 | R09 | W20 | A-14/A-15 | Communication messages, channels, timing and reach |
| F-13 | R10/R06 | W19 | A-16/A-17 | Career action evidence and teaching fallback |
| F-14 | R10 | — | A-04/A-33 | Review cadence |
| F-15 | R11 | — | A-22/A-28 | Data/software reuse and irrigation audience |
| F-16 | R12/R02/R15 | W24 | A-26/A-10 | Credible dependency access; signatures not treated as score by themselves |
| F-17 | R13 | W10/W11 | A-09/A-34 | Workload; W11 counted once |
| F-18 | R13 | W9 | A-11 | Calendar and slipped-start response |
| F-19 | Excluded | W1 | A-01 excluded | Part A/B2 registration issue; no score recovery claimed |
| F-20 | R14 | W23 | A-25 | Includes E2 compute/storage concern |
| F-21 | R17 | W22 | A-10 | Risk triggers and availability |
| F-22 | R15 | W8 | A-27 | Resource credibility, no Part A budget changes |
| F-23 | R16 | W5 | A-03 | Low-value numbering consistency |
| F-24/F-28 | Excluded | W7 | A-06 excluded | Part A/B2 ethics-table/pointer issues |
| F-25 | Excluded | W3 | A-30 excluded | B2 cosmetic issue |
| F-26 | Excluded | W6 | A-32 excluded | Part A cosmetics |
| F-27 | Excluded | — | A-31 excluded | B2 inter-relationship declaration |
| F-29 | Excluded | — | A-05 excluded | Career-break documentation/formal issue |
| W25 | Preserve | W25 | No corrective action | 12-month secondment and M25–M30 placement are accepted design features |

**Annex A coverage beyond the register:** E1's phenology, physiological rule, replication and crop-loss arrangements are in R02/R15; its horticultural dissemination issue is in R11. E2-a/b/c/d/e/f are covered by R03/R02/R01/R11/R14/R01 respectively. E3's extra CDP finding is in R10; its inter-relationship and ethics-pointer observations are excluded; its end-user co-creation observation is a strength to retain in R08/R09. All in-scope weaknesses in the consensus evaluation and three lenses are covered above without treating overlapping observations as separate score gains.

### Open-decision disposition

| Decision | Answer/route |
|---|---|
| OD-E1 | Excluded: Part A participant registration |
| OD-E2 | R07: held only with award evidence; otherwise studies in progress or omit disputed credential |
| OD-E3 | Excluded: B2 CV details; existing relevant evidence can support R07 without CV edits |
| OD-E4 | R05: usable sourced examples supplied; totals/current commitments still require owners |
| OD-E5 | R01/R03: concrete transfer/model options supplied; archive facts and access remain unresolved |
| OD-E6 | R02/R03: dimensioned proposed design and physiological/analysis rules supplied; feasibility and numeric reference limits need data |
| OD-E7 | R13: February calendar option, conditional March/M4 alternatives and failed-window fallback |
| OD-E8 | R08: public dated AgroVIR reach supplied; eligible subset, national crop area and secured site hectares not established |
| OD-E9 | R09: concrete proposed communication plan; host-channel access remains a factual dependency |
| OD-E10 | R11: repository/licence/preprint/release choices supplied; ownership authority still required |
| OD-E11 | R12: separate credible participation from contract execution; no fabricated agreement status |
| OD-E12 | R14: concrete hosting specification and remote-compute alternative; actual provision requires ATK/ELTE input |
| OD-E13 | R15: resource priorities and lean alternatives; no invented funding allocation |
| OD-E14 | Excluded: Part A ethics answers |
| OD-E15 | R06: verified course names plus proposed timetable, bespoke-module and host-teaching fallbacks |
| OD-E16 | R10/R11: grant-package, mentoring/peer-teaching and irrigation-dissemination options; no unverified future call or event date |
| OD-E17 | R04: tomato CWSI, processing-tomato ML and ET references supplied with comparison |
| OD-E18 | R07: evidence structure supplied; actual DrR version/functions and certificate details unresolved; B1 use only |
| OD-E19 | Excluded: B2 declaration |
| OD-E20 | R16: consistent renumbering if chart can be regenerated; otherwise keep existing gap |

## 5. Revision order and Part B1 cut budget

### Recommended revision packages

| Package | Answers/actions | What must fit in B1 | Completion criterion |
|---|---|---|---|
| 1 — scientific credibility | R01–R03; A-20/A-21 | Common-predictor method, sensing limits, actual/proposed design dimensions, reference rule, named model/calibration, blocked validation and operational decision gate | An agronomy and EO/ML reader can assess the experiment without waiting for D1.2 |
| 2 — delivery credibility | R05/R06/R12/R13; A-18/A-24/A-26/A-11/A-34 | Supervision evidence, first-block continuity, real access status, field/calendar assumptions, first-quarter workload | Critical dependencies have specific owners and credible outcomes if they fail |
| 3 — Impact | R08–R11; A-12–A-17/A-22/A-28 | Direct versus addressable reach, targeted communication, release schedule and dated career actions | Outputs, audiences, uptake evidence and limits are distinguishable |
| 4 — supporting precision | R04/R07/R14/R15/R17 | Comparator references, researcher evidence, host provision, resource sources and specific risks | Generic assertions have been replaced with evidence or clearly adopted plans |
| 5 — consistency | R10/R16; A-02/A-03/A-04/A-33 | MSc wording, CDP cadence and cross-references | No contradiction created across B1 text, tables and Gantt |

Do not wait for every owner response before banking supported improvements. Conversely, do not represent the scientific package as complete while instrument, field or reference feasibility remains unknown. References, communication planning and open-science choices can progress while the scientific facts are being resolved.

### Reuse the ESR cuts once each

The ESR estimates **25 lines** recoverable on B1 pp.1–7, **five** on pp.8–9 and **six** on p.10. These are estimates at the submitted layout, not verified savings for the future rewrite. Tables, footnotes and page breaks make a line on one page non-interchangeable with a line elsewhere. The Gantt nearly fills the bottom of B1 p.9; §3 begins on p.8; the §2.1 table crosses pp.5–6.

The ledger below allocates each listed cut to one purpose. It deliberately reallocates some of the ESR's editorial-first cuts to the higher-value scientific package. Do not also charge those same cuts to the original A-actions.

| Reserved cut IDs | Location/content to compress | ESR estimated saving | Allocate once to | Guard |
|---|---|---:|---|---|
| CUT-18, CUT-9, CUT-22 | Repeated feasibility/predictor/partner prose in §1.1–1.2 | 4 lines | R01/R03 transfer and named-model specification | Retain scientific role assignments and common-predictor logic |
| CUT-19, CUT-23, CUT-25 | Repeated UAV explanation, career sentence and generic opening problem prose | 5 | R02 dimensions/reference/phenology | Retain in B1 that UAV does not replace primary Sentinel evidence |
| CUT-1 | Repeated career trajectory in §1.1 | 3 | R07 evidence plus only essential R13 readiness detail | Combine A-08/A-09 evidence once; do not repeat training stays in two sections |
| CUT-7 | Repeated K1–K14 enumeration in §2.3 | 3 | R01/R02 overflow | KPI detail remains in §3.1 |
| CUT-10 | Host EU-project list in §1.3 | 2 | R05 personal supervision evidence | Preserve a short B1 host-capacity cue in §3.2; do not assume B2 duplication makes every B1 fact expendable |
| CUT-11, CUT-12 | Repeated placement data-handling sentence and Stage 3 description | 2 | R08 magnitude | Preserve in B1 consent/data limits and the evidence-to-MVP gate elsewhere |
| CUT-13, CUT-8 | Repeated career/secondment prose in §2.1 | 3 | R09 communication specificity | Keep the mechanism and value of the secondment/placement |
| CUT-17 | Audience list repeated above §2.2 table | 2 | R09 reach/channels or R11 release specifics | Audiences remain explicit in the table |
| CUT-20 | Generic two-way-transfer opener | 1 | R06/R10 assessed training/career commitments | Preserve the two concrete directions of knowledge transfer |
| CUT-5, CUT-14 | Administrative outputs and redundant five-WP summary in §3.1 | 3 | R17 missing risk triggers and R13 effort clarification | Keep science, WPs, PM, gates and core deliverables |
| CUT-15, CUT-16 | Compress WP5 verbs and K5 wording | 2 | R13 start window/contingency | Retain quarterly reviews and **scheduled-versus-valid observation accounting**; do not delete the denominator to save a line |
| CUT-2, CUT-3 | Conditional female-student participation sentences in §3.2 | 4 | R14 concrete host/compute provision | Preserve the accepted gender dimension in §1.2; team composition is not a replacement for research-content analysis |
| CUT-4 | Repeated post-MSCA MVCRI narrative in §3.2 | 2 | R12 actual access/dependency status | Keep “no core in-action validation role” and the optional continuation route |

**The 36-line pool cannot hold the full answer bank.** The science package alone needs more than replacing one hedged sentence. Use compact structured clauses or one integrated method/design table, replace generic prose in place, and reduce repetition within the same B1 region. Treat the ESR's approximately five spare lines on p.7 and four on p.10 as a safety margin. They cannot automatically fund footnotes on p.1 or a new risk row above the p.9 Gantt.

**Additional in-place compression candidates, not already banked:** consolidate the four repeated representations of the pipeline in §1.1, §1.2, §2.3 and §3.1 while preserving each section's distinct purpose; merge redundant “independent Agricultural Data Scientist” descriptions; use the same short asset names in the open-science and dissemination rows. Savings are unmeasured and must not be counted until the later document is rendered.

**Preserve:** falsifiability, independent physiology, blocked historical validation, freeze before prospective outcomes, primary results before adaptation, supplementary-only UAV status, one-crop/two-season limits, two-way knowledge transfer, placement rationale, rights layers, evidence-based MVP gates and honest water-saving boundaries. Calendar/PM numbers can change only as a coherent adopted redesign, not as a space-saving edit. Keep the source/output right distinctions in the exploitation strand; minor timing wording may need alignment if contracts follow submission.

### Handoff to the later editor

1. Record the selected R-options and owner facts with their evidence and date; leave rejected alternatives out of B1.
2. Insert the smallest assessable scientific specification first. Do not hide all key design decisions in future deliverables.
3. Update related objectives, methods, risks, effort and Gantt together for every accepted scientific/calendar change.
4. Apply each cut once and maintain a region-level insertion/cut ledger. Check B1 pp.1–7, pp.8–9 and p.10 separately.
5. Re-render at compliant typography and verify the ten-page limit, footnotes, table splits and Gantt. No shrinking of body font is proposed here.
6. Check that every number is either supported fact, adopted target or explicitly labelled scenario; remove unsupported assertions of access, completed training, signed agreements, users, savings or accuracy.
7. Reassess the three criteria as a whole against the revised B1. Record unresolved weaknesses; do not declare score gains just because a sentence or reference was added.

## 6. Sources and verification boundary

- [Submitted FIELDWISE PDF](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf): B1 PDF pp.24–33, internal pp.1–10. Text reviewed; scientific-method and implementation/Gantt/host pages visually inspected. SHA-256 verified as `c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe`.
- [Simulated ESR Markdown](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/plans/reports/FIELDWISE_ESR_2026-09-08.md) and [JSON packet](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/plans/reports/FIELDWISE_ESR_2026-09-08.json): consensus evaluation, Annex A, F-01–F-29, A-01–A-34, cut pool and OD-E1–OD-E20 cross-checked. Repository snapshot: `19a6d4c392866cb6e93fc64ab95633fb4d841261`.
- [HE MSCA evaluation form V2.2, 17 December 2025](https://github.com/JozsefKiss90/proposal_orchestrator/blob/ESR/docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf): governing assessment aspects and score descriptors. Evaluators assess the submitted application; future potential improvements do not repair the already submitted version's score.
- [Official call page](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-MSCA-2026-PF-01-01), [REA application guidance](https://rea.ec.europa.eu/funding-and-grants/horizon-europe-marie-sklodowska-curie-actions/horizon-europe-msca-how-apply_en), and [official 2026–2027 MSCA work programme](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2026-2027/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf). The work-programme PDF downloaded from the Commission was byte-identical to the repository copy. The dynamic topic page provided limited readable content; operative detail was checked in the programme/template, not inferred from the topic URL.
- [Official application template V5.0, 27 March 2026](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/af/af_he-msca-pf_en.pdf): Part B1 headings, scope of the commitment-letter requirement and placement-letter removal.
- Additional primary technical, policy, institutional and company evidence is linked at its point of use in R01–R11. Publicly documented institutional experience is distinguished from unverified project-specific availability.

**Deliverable boundary:** This brief supplies scoring-improvement answers and revision choices. It does not certify scientific power, validate a trained model, secure land/equipment/staff, confirm contracts, select a grant start date, predict an evaluation score or edit/re-submit any proposal component. Those unresolved facts are explicitly identified so the next revision can improve credibility without fabricating evidence.
