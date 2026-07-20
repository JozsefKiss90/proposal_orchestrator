---
id: PS-implementation-3.1
title: Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages
node_type: proposal_section
evidence_strength: synthesis
tier: tier5
section_slug: implementation
criterion: Implementation
sub_section_id: '3.1'
source_refs:
- tier: 2
  source_path: docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json
- tier: 2
  source_path: docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
- tier: 2
  source_path: docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
- tier: 3
  source_path: docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json
- tier: 3
  source_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
- tier: 3
  source_path: docs/tier3_project_instantiation/architecture_inputs/risks.json
- tier: 3
  source_path: docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
- tier: 3
  source_path: docs/tier3_project_instantiation/call_binding/confirmation_checklist.json
- tier: 3
  source_path: docs/tier3_project_instantiation/call_binding/selected_call.json
- tier: 3
  source_path: docs/tier3_project_instantiation/project_brief/concept_note.md
- tier: 3
  source_path: docs/tier3_project_instantiation/project_brief/project_summary.json
- tier: 3
  source_path: docs/tier3_project_instantiation/project_brief/strategic_positioning.md
- tier: 4
  source_path: docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
- tier: 4
  source_path: docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json
- tier: 4
  source_path: docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json
- tier: 4
  source_path: docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json
provenance_detail: 'Graph-authored (ticket 8) from docs/tier5_deliverables/proposal_sections/implementation_section.json sub_section 3.1. Section overall_status=inferred; source claim distribution={''confirmed'': 85, ''inferred'': 11}. Per-node evidence_strength=synthesis: drafted evaluator narrative synthesises confirmed Tier-3/2B facts and never lands as a source_grounded fact.'
---

3.1  QUALITY AND EFFECTIVENESS OF THE WORK PLAN, ASSESSMENT OF RISKS AND APPROPRIATENESS OF THE EFFORT ASSIGNED TO WORK PACKAGES

Work-Plan Structure

The fellowship is organised into five work packages spanning 24 months. WP1 through WP3 carry the scientific and technical research content and are structured around the project's two-branch architecture — a diagnostic branch (WP1) and a prognostic/decision branch (WP2) validated in the field (WP3). WP4 and WP5 are MSCA-PF structural packages required by the instrument: WP4 (Training, supervision and two-way transfer of knowledge) is led by Dr. András Jung, and WP5 (Dissemination, exploitation, communication and management) is led by Dr. Rositsa Cholakova. The fellow's 24 person-months are distributed across the five work packages and sum to exactly 24, consistent with the confirmed European Fellowship duration. Supervisor and host effort is in-kind and not included in the fellow's person-month count.

The sequencing logic is explicit: WP1 must produce calibrated field-state posterior estimates before WP2 can calibrate the decision engine on them, and WP3 can begin collecting ground truth in parallel with WP1 during the growing seasons rather than waiting for WP1 to close. This staging — an overlapping, not purely sequential, structure — is what allows a 24-month fellowship to accommodate data acquisition, model development, field validation and demonstrator integration without compressing any phase so tightly that a single delay propagates through the whole plan.

WP1 — Probabilistic multi-sensor diagnosis of the field state (months 1–14; 8 person-months; lead: Dr. Rositsa Cholakova)

WP1 builds the diagnostic branch of the project: it acquires and harmonises the full multi-sensor Earth-observation and meteorological data stack for tomato field-state monitoring in Hungary, and uses that stack to estimate the latent field state — root-zone soil moisture and crop water status (RQ3) — as calibrated posterior distributions rather than point estimates. The confirmed data sources are: Sentinel-1 SAR and Sentinel-2 optical (open Copernicus data), PlanetScope high-resolution imagery secured through the Planet platform and API (RQ8), and ERA5 meteorological reanalysis from ECMWF.

The project adopts Route B, the homogeneous-patch proxy (RQ2), as the primary diagnostic route: a nearby homogeneous patch matched on soil and climate characteristics whose biology covaries with the target tomato field and which the coarser Sentinel pixel can resolve cleanly, sidestepping the sub-pixel heterogeneity problem that makes direct satellite inference difficult on small horticultural plots. The methodological architecture also defines Route A — a direct one-step probabilistic fusion model (Bayesian hierarchical model or Gaussian process) that takes the full multi-sensor covariate stack straight to a field-state posterior without an intermediate proxy pixel — as an alternative and, if Route B's covariation assumption fails validation in WP3, as a fallback. These two interchangeable routes feed a single shared decision engine downstream in WP2.

Three tasks structure WP1. T1-01 (Acquire and harmonise multi-sensor EO and meteorological data, months 1–6) establishes the geospatial and time-series data platform: Sentinel-1, Sentinel-2, PlanetScope, ERA5 and ground-level field-observation data are ingested, quality-controlled and harmonised over the Hungarian tomato field boundaries. Month 6 is also the target for MS1 (the multi-sensor data pipeline operational milestone, coinciding with delivery of the Data Management Plan), ensuring the platform is functional in time to ingest a full growing season before calibration begins. T1-02 (Implement Route A direct probabilistic fusion and Route B homogeneous-patch proxy, months 4–10) implements the two diagnostic routes in code, in parallel with the later stages of T1-01 data harmonisation. T1-03 (Calibrate diagnostic branch and produce field state posterior estimates, months 8–12) takes the harmonised data from T1-01 and the implemented models from T1-02, calibrates the diagnostic branch, and produces the calibrated field-state posteriors that WP2 requires. WP1's formal deliverable is D1-01 — Diagnostic model specification and calibration report — due at month 14, providing a two-month consolidation window after the core modelling in T1-03 ends.

WP2 — Uncertainty-aware decision engine and demonstrator integration (months 6–20; 7 person-months; lead: Dr. Rositsa Cholakova)

WP2 builds the prognostic branch and integrates the full observation-to-decision pipeline. T2-01 (Implement uncertainty-aware AquaCrop calibration and parameter posterior, months 10–14) takes the calibrated field-state posterior estimates from T1-03 and calibrates the AquaCrop crop model in an uncertainty-aware manner, retaining an honest parameter posterior rather than collapsing to a single overconfident parameter set. This is the critical interface through which the diagnosed state drives the crop model; uncertainty from the diagnosis propagates forward into AquaCrop's parameter distribution and from there into the simulated outcomes. The approach builds on established uncertainty-aware crop-model calibration methods in the literature (doi:10.1016/j.envsoft.2022.105556, cited in the project risk register). T2-02 (Develop counterfactual irrigation simulation and WUE-based decision engine, months 12–15) takes the uncertainty-aware AquaCrop calibration from T2-01 and develops the decision engine: counterfactual irrigation simulations are run over weather ensembles, candidate irrigation decisions are scored by expected water-use efficiency (the confirmed decision objective, RQ6), and the option that best improves water-use efficiency under the joint weather and model uncertainty is recommended. T2-03 (Build and integrate research demonstrator web MVP, months 14–18) integrates the full observation-to-decision pipeline into a standalone research demonstrator — a web MVP that presents irrigation recommendations together with their uncertainty. The demonstrator is explicitly scoped as a research artefact at TRL 3–4 (RQ10), consistent with what a 24-month research fellowship can realistically deliver and appropriate to the novel, probabilistic methodology it embodies. WP2's deliverable is D2-01 — Decision engine and demonstrator software — due at month 20.

WP3 — Field validation, ground truth and uncertainty calibration (months 8–24; 5 person-months; lead: Dr. Rositsa Cholakova)

WP3 validates the diagnostic branch and the decision recommendations against empirical ground truth collected at Hungarian tomato farms accessed through the associated partner AgroVIR. This WP is where the fellow's core expertise is most directly load-bearing: Dr. Rositsa Cholakova's PhD addressed the non-destructive evaluation of the physiological status of drought-stressed tomato plants (doi:10.2139/ssrn.5492527, summa cum laude, 2020), and her expertise in non-destructive plant-stress phenotyping is the project's biological ground-truth engine.

Three tasks structure WP3. T3-01 (Design and run field validation protocol on Hungarian tomato farms, months 8–18) designs the measurement protocol and runs field campaigns at the AgroVIR-accessed tomato sites, collecting non-destructive physiological ground truth: chlorophyll fluorescence, stomatal conductance, canopy and leaf temperature, and spectral reflectance (RQ4, all four measurements operator-confirmed). Starting at month 8 ensures that at least one full growing season is captured for calibration comparison before the WP1 diagnostic branch closes its calibration phase. T3-02 (Assess uncertainty calibration quality against RQ5 target, months 13–20) evaluates whether the diagnostic posterior estimates satisfy the operator-confirmed calibration criterion: 90% prediction intervals containing the truth approximately 90% of the time (RQ5). This task depends on T1-03 having produced field-state posterior estimates; it runs T1-03's outputs against the RQ4 ground-truth measurements and produces the calibration evidence that determines whether the pilot-success criterion (RQ7: the RQ5 target met on the validation set) is met. T3-03 (Run co-located patch-covariation campaign for Route B validation, months 10–22) executes the operator-confirmed empirical test of Route B's covariation assumption (RQ9): the target tomato crop and the chosen proxy patch are measured simultaneously in a co-located seasonal campaign, and statistical covariation between the two is established from data rather than assumed. This task depends on T1-02 having implemented Route B before the campaign tests it. WP3 closes at month 22 with MS5 (field validation and uncertainty calibration complete) and delivers D3-01 — Field validation dataset and uncertainty calibration report — at month 24.

WP4 — Training, supervision and two-way transfer of knowledge (months 1–24; 2 person-months; lead: Dr. András Jung)

WP4 is the MSCA-PF structural training and knowledge-transfer package. Two tasks: T4-01 (Prepare, submit and periodically review Career Development Plan, months 1–3) produces D4-01 — Career Development Plan — at month 3. The CDP is prepared jointly by Dr. András Jung and Dr. Rositsa Cholakova and must be submitted as a project deliverable at the beginning of the action (SR-04), then reviewed and updated during the fellowship. It will set the specific, measurable training and career targets for the fellowship — publication planning, training hour targets, co-supervision, and career-progression milestones — that are intentionally not pre-asserted in this proposal; none were operator-provided at proposal stage, and the appropriate moment to fix them is at the start of the action, jointly with the supervisor, so they reflect the actual state of the fellow's career at the time of commencement. T4-02 (Deliver structured transferable-skills training and supervision sessions, months 1–24) runs throughout the full fellowship, providing structured training that integrates the MSCA-PF mandatory transferable-skills dimensions (SR-03): digital and AI skills (including the responsible use of generative AI in remote-sensing and crop-water modelling workflows and scientific coding); knowledge valorisation and innovation and entrepreneurship (translating the uncertainty-aware decision-support demonstrator toward user uptake); research integrity; and open science and FAIR data stewardship. Dr. András Jung supervises through regular research reviews within the host's geoinformatics and remote-sensing group.

The two-way transfer of knowledge that WP4 structures is genuine and load-bearing in both directions. The fellow brings to the host: plant-physiology and non-destructive stress-phenotyping expertise that constitutes the project's biological ground truth for tomato (RQ4) — expertise the host's geoinformatics group does not possess independently. The host provides to the fellow: geoinformatics, remote sensing, hyperspectral imaging, field spectroscopy, and multisensor-drone-fusion methods and infrastructure — the EO methodology backbone of the project that the fellow is acquiring through the fellowship. This exchange is not a formality; neither party can execute this project without what the other brings.

WP5 — Dissemination, exploitation, communication and management (months 1–24; 2 person-months; lead: Dr. Rositsa Cholakova)

WP5 handles open-science dissemination, exploitation logic, communication to relevant audiences, and lightweight project management and ethics oversight. Two tasks: T5-01 (Develop and implement open-science dissemination and communication strategy, months 1–24) implements the open-access publication strategy, open research software and data releases, and communication to the host's geoinformatics and remote-sensing community and to Hungarian tomato growers through AgroVIR. T5-02 (Manage project coordination, reporting and ethics oversight, months 1–24) manages day-to-day coordination, progress reporting, and ongoing ethics compliance.

WP5 carries two early deliverables. D5-01 — Data Management Plan — is due at month 6, establishing FAIR data stewardship for the multi-sensor dataset, the calibration and validation datasets, and the research demonstrator outputs. D5-02 — Dissemination and exploitation plan — is also due at month 6, setting out the publication strategy, demonstrator exploitation logic, and communication targets in a document that guides subsequent dissemination activities. Early delivery of both plans ensures that open-science and exploitation commitments are formalised before the main research results begin to emerge.

Gantt Chart

The chart below shows months elapsed (not dates) as required. Symbols: ■ = active; D = deliverable due; ◆ = milestone. No secondments or non-academic placements are included in the fellowship plan.

Row                                              | M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11 M12 M13 M14 M15 M16 M17 M18 M19 M20 M21 M22 M23 M24
-------------------------------------------------|----------------------------------------------------------------------------------------------------
WP1 Probabilistic multi-sensor diagnosis (8 PM)  |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T1-01 Acquire/harmonise EO + met. data          |  ■   ■   ■   ■   ■   ■
 T1-02 Implement Route A / Route B               |              ■   ■   ■   ■   ■   ■   ■
 T1-03 Calibrate + produce field-state posteriors|                              ■   ■   ■   ■   ■
 D1-01 Diagnostic model spec. + calib. report    |                                                  D
-------------------------------------------------|----------------------------------------------------------------------------------------------------
WP2 Decision engine + demonstrator (7 PM)        |                       ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T2-01 AquaCrop calibration + parameter post.    |                                         ■   ■   ■   ■   ■
 T2-02 Counterfactual simulation + WUE engine    |                                             ■   ■   ■   ■
 T2-03 Research demonstrator web MVP             |                                                  ■   ■   ■   ■   ■
 D2-01 Decision engine + demonstrator software   |                                                                   D
-------------------------------------------------|----------------------------------------------------------------------------------------------------
WP3 Field validation, ground truth (5 PM)        |                          ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T3-01 Field protocol + campaigns                |                          ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T3-02 Uncertainty calibration assessment        |                                             ■   ■   ■   ■   ■   ■   ■   ■
 T3-03 Co-located patch-covariation campaign     |                                    ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 D3-01 Field validation dataset + calib. report  |                                                                                       D
-------------------------------------------------|----------------------------------------------------------------------------------------------------
WP4 Training, supervision, transfer (2 PM)       |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T4-01 Prepare/submit Career Development Plan    |  ■   ■   ■
 T4-02 Structured training + supervision         |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 D4-01 Career Development Plan                   |          D
-------------------------------------------------|----------------------------------------------------------------------------------------------------
WP5 Dissemination, exploitation, mgmt (2 PM)     |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T5-01 Dissemination + communication strategy    |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 T5-02 Coordination, reporting + ethics          |  ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■   ■
 D5-01 Data Management Plan                      |               D
 D5-02 Dissemination and exploitation plan       |               D
-------------------------------------------------|----------------------------------------------------------------------------------------------------
MILESTONES                                       | M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11 M12 M13 M14 M15 M16 M17 M18 M19 M20 M21 M22 M23 M24
MS1 Multi-sensor pipeline operational; DMP del.  |               ◆
MS2 Diagnostic method v1; calibrated posteriors  |                                         ◆
MS3 Decision engine integrated (WUE + AquaCrop)  |                                              ◆
MS4 Research demonstrator exercises full pipeline|                                                        ◆
MS5 Field validation + uncertainty calib. done   |                                                                            ◆
MS6 Results disseminated; outcomes consolidated  |                                                                                       ◆

Dependency Logic and Critical Path

Three cross-WP task-level dependency edges define the logical sequence of the work plan. Edge (1): T1-03 → T2-01 — the calibrated field-state posterior estimates produced by T1-03 (WP1) are the driving inputs for the uncertainty-aware AquaCrop calibration in T2-01 (WP2). The decision engine cannot be meaningfully calibrated until the diagnostic branch has produced its posteriors; this edge is the primary scientific dependency in the project and defines the timing of WP2's opening. Edge (2): T1-03 → T3-02 — the uncertainty calibration quality assessment in T3-02 (WP3) requires the posterior estimates from T1-03 to evaluate prediction-interval coverage against the RQ5 target. T3-02 cannot begin until T1-03 outputs are available; it is timed to start at month 13, one month after T1-03's nominal end. Edge (3): T1-02 → T3-03 — the co-located patch-covariation campaign in T3-03 validates Route B as implemented in T1-02; the campaign must measure the proxy that exists in code before it can validate it. T3-03 starts at month 10, consistent with T1-02 ending at month 10. No cycles exist in the dependency graph; a Kahn's topological sort over the 18-node, 3-edge directed graph confirms acyclicity.

The primary critical path runs through T1-01 (months 1–6) → T1-02 (months 4–10) → T1-03 (months 8–12) → T2-01 (months 10–14) → T2-02 (months 12–15) → T2-03 (months 14–18), terminating at MS4 (month 18). The WP1-to-WP2 handover at T1-03 → T2-01 is the most schedule-sensitive dependency: a slip in T1-03 propagates directly to T2-01 and, through T2-01, to T2-02 and T2-03. The schedule provides a two-month buffer between T1-03's nominal end (month 12) and D1-01's due date (month 14), and a further two-month buffer between T2-03's end (month 18) and D2-01's due date (month 20), absorbing minor slippage without affecting the downstream validation programme.

Milestone Schedule

Six milestones are defined, each with a verifiable achievement criterion that confirms the state of the project at the milestone moment rather than simply listing activities completed.

MS1 — Multi-sensor data pipeline operational; Data Management Plan delivered (month 6). Verifiable criterion: Sentinel-1, Sentinel-2, soil-sensor and weather data are ingested, quality-controlled and harmonised over the field boundaries on the geospatial/time-series platform; the Data Management Plan is delivered as an open-science deliverable by month 6. This milestone is the first gate of the project: it confirms that the data infrastructure on which all downstream modelling depends is operational and that the open-science obligations are in place.

MS2 — Diagnostic method v1 producing calibrated field-state posteriors (month 12). Verifiable criterion: Route A and/or Route B produce posterior estimates of the target latent field state (root-zone soil moisture, crop water status) with explicit uncertainty over at least one growing season's data; route scope (RQ2) and field-state definition (RQ3) recorded as decided. This milestone marks the de facto completion of WP1's core scientific content and verifies that the posteriors feeding WP2 and WP3 are available.

MS3 — Uncertainty-aware decision engine integrated (month 15). Verifiable criterion: AquaCrop is calibrated retaining an honest parameter posterior; counterfactual irrigation simulations run over weather ensembles; the recommendation logic selects irrigation decisions by water-use efficiency under uncertainty, end to end from a diagnosed field state. This milestone confirms that the full observation-to-decision chain is functioning and that the confirmed decision objective (water-use efficiency, RQ6) has been operationalised in the engine.

MS4 — Standalone research demonstrator exercises the end-to-end pipeline (month 18). Verifiable criterion: the web MVP runs the full observation-to-decision pipeline and presents irrigation recommendations with their uncertainty for at least one field case; TRL target (RQ10) recorded. This milestone produces the tangible research artefact that can be presented to field partners for feedback and used in WP3 validation.

MS5 — Field validation and uncertainty calibration complete (month 22). Verifiable criterion: ground truth collected (RQ4); uncertainty-calibration metrics evaluated — prediction-interval coverage assessed against the 90% nominal target (RQ5); Route B patch-covariation tested (RQ9); pilot-success criteria (RQ7) applied to the demonstrator. This is the scientific credibility gate: it determines whether the framework's headline commitment to honest uncertainty has been met, and whether Route B's covariation assumption holds at the validation sites.

MS6 — Results disseminated and fellowship outcomes consolidated (month 24). Verifiable criterion: at least one open-access publication submitted covering the probabilistic fusion-to-decision framework; open data/models released under FAIR principles; dissemination/exploitation and communication actions executed per the plan. This terminal milestone confirms that the scientific results are publicly available and that the open-science commitments formalised in D5-01 and D5-02 have been honoured.

Deliverables

The six deliverables are distributed across the WPs as follows. D4-01 (Career Development Plan, month 3, WP4, report) is the earliest — establishing the fellow's training and career-development framework at the start of the action, in compliance with SR-04. D5-01 (Data Management Plan, month 6, WP5, report) and D5-02 (Dissemination and exploitation plan, month 6, WP5, report) follow at month 6, ensuring open-science and exploitation planning is in place before results emerge. D1-01 (Diagnostic model specification and calibration report, month 14, WP1, report) captures the diagnostic branch methodology and calibration evidence. D2-01 (Decision engine and demonstrator software, month 20, WP2, software) delivers the integrated decision engine and web MVP. D3-01 (Field validation dataset and uncertainty calibration report, month 24, WP3, dataset) closes the fellowship with the empirical evidence base for the framework's calibration claims.

Effort Allocation

The fellow's 24 person-months are allocated as follows: 8 PM to WP1, the largest block, reflecting the central and most technically novel component of the project — the probabilistic multi-sensor diagnostic branch, which requires modelling expertise, data harmonisation work, and calibration iterations; 7 PM to WP2, the decision engine and demonstrator, which builds directly on WP1 outputs and requires substantial integration and software development work; 5 PM to WP3, the field validation, which is intensive during growing seasons but overlapping in time with WP1 and WP2 rather than purely sequential; 2 PM each to WP4 and WP5, the MSCA-PF structural packages for training, management and dissemination. The effort distribution is proportionate to the scientific complexity and duration of each WP: the three research WPs (WP1–WP3) account for 20 of the 24 person-months (83%), consistent with a research-intensive fellowship. The 4 PM allocated to WP4 and WP5 combined is sufficient for the CDP, training programme, DMP, dissemination plan, and ongoing management given the single-researcher, single-beneficiary structure.

Risk Assessment

The risk register covers ten identified hazards across four categories, grounded in the project's methodology vault risk register (METH-RISK-002). Each risk is presented with its assessed likelihood, impact, and mitigation; contingencies are provided for the highest-impact risks.

Data-Access Risks

RISK-01 — PlanetScope cost/access constraining high-resolution coverage of small tomato plots (originally: medium probability, high impact). This risk is materially resolved by the operator-confirmed pre-proposal decision (RQ8) that PlanetScope access has been secured through the Planet platform and API. The Sentinel-1 and Sentinel-2 open-data stack remains the open-data core; PlanetScope provides the high-resolution enhancement for small-plot inference. The mitigation (treating PlanetScope as an optional enhancement built on a confirmed open-data core) was prudent design; the execution risk is now low.

RISK-02 — Spatial and temporal resolution harmonisation across heterogeneous sources failing or degrading fusion quality (high probability, medium impact). Sentinel-1 (10–20 m), Sentinel-2 (10 m), ERA5 (~31 km) and plot-level field observations operate at radically different scales. Mitigation: a geospatial and time-series data platform with quality-control procedures, temporal compositing and explicit resolution handling in T1-01. Contingency: restrict fusion to the sources that harmonise reliably and treat problematic sources as covariates at their native resolution.

RISK-03 — Cloud cover limiting Sentinel-2 optical availability; dense tomato canopy reducing Sentinel-1 SAR retrieval accuracy (high probability, medium impact). These are the complementary weaknesses of the two primary free sensors. Mitigation: lean on Sentinel-1 SAR through cloud-covered periods; apply cloud masking; use vegetation-aware SAR retrieval. The dual-sensor design is explicitly constructed so that each sensor compensates for the other's worst-case conditions. Contingency: cross-sensor gap-filling using radar-informed optical estimates.

Validation Risks

RISK-04 — Sparse ground-truth coverage leaving the validation statistically under-powered (medium probability, high impact). Mitigation: the T3-01 field validation protocol maximises ground-truth density at the AgroVIR-accessed Hungarian tomato farms; the non-destructive physiological measurement protocol (RQ4) is cost-effective relative to destructive sampling and can be deployed across multiple plots per visit. Contingency: prioritise ground truth at a focused pilot site and supplement with published reference datasets.

RISK-05 — Route B's covariation assumption — that the chosen homogeneous proxy patch genuinely covaries with the target tomato crop — not holding, invalidating the proxy (medium probability, high impact). This is the most structurally important risk in the project. If Route B's central empirical assumption fails, the primary diagnostic route is invalid. The mitigation is methodologically built in by design: the co-located seasonal campaign (T3-03, RQ9) measures the target tomato crop and the proxy patch simultaneously and establishes statistical covariation from data rather than assuming it. Covariation is measured, not assumed. Contingency: if covariation cannot be demonstrated, Route A (direct one-step probabilistic fusion) becomes the main diagnostic route.

RISK-06 — The framework's headline commitment to honest uncertainty failing calibration — 90% prediction intervals not containing the truth approximately 90% of the time (medium probability, high impact, affecting OBJ-1, OBJ-2 and OBJ-3 simultaneously). This is the risk to the project's central scientific claim. Mitigation: uncertainty-aware calibration is used end-to-end throughout the framework, from the diagnostic posterior through AquaCrop parameter inference; the RQ5 prediction-interval coverage criterion is built into the validation protocol as MS5's verifiable criterion. Contingency: recalibrate posteriors post-hoc and report calibration honestly, narrowing claims to the calibrated regime rather than asserting general validity.

Model-Complexity Risks

RISK-07 — Route A being too computationally or methodologically demanding within the 24-month fellowship given available expertise, validation data and compute (medium probability, high impact). Mitigation: Route B is the primary diagnostic route (RQ2), confirmed by the operator before the proposal was written; the project's effort budget is not split equally between routes. Route B is sufficient to deliver all scientific objectives; Route A is the rigorous alternative that, if tractable, provides a comparison baseline. Contingency: adopt Route B as the sole main route and treat Route A as an extension for future work.

RISK-08 — AquaCrop calibration collapsing to a single overconfident parameter set, breaking the uncertainty chain and producing falsely confident irrigation decisions (medium probability, high impact). Mitigation: the uncertainty-aware AquaCrop calibration approach implemented in T2-01 explicitly retains a parameter posterior, building on established uncertainty-aware crop-model calibration approaches in the literature (doi:10.1016/j.envsoft.2022.105556, cited in the project risk register). Propagating parameter uncertainty forward into the decision is not an optional enhancement but the core commitment of the prognostic branch. Contingency: ensemble over plausible parameter sets if a full posterior is computationally intractable, propagating ensemble spread into the decision.

RISK-09 — Sensor calibration and integration complexity degrading signal quality across the heterogeneous multi-sensor stack (medium probability, medium impact). Mitigation: a quality-control pipeline in T1-01 and sensor comparison in the T3-01 validation layer. Contingency: reduce to the reliably calibrated sensor core and document excluded sensors as extension points.

Operationalisation Risks

RISK-10 — The research demonstrator not reaching a usable pilot state within the fellowship, given the scarcity of unified operational frameworks for multi-sensor crop-water decision support at scale (medium probability, medium impact). Mitigation: the TRL target is set explicitly at research prototype, TRL 3–4 (RQ10), at proposal stage; AgroVIR provides farmer access and field feedback but does not own or operate the tool; the demonstrator is framed throughout as a research artefact rather than an operational product. The TRL scope management is built into the project's definition of success (OBJ-4) and does not require external negotiation during execution.

Overall Risk Posture

Of the ten risks, six are classified at high impact (RISK-01, RISK-04, RISK-05, RISK-06, RISK-07, RISK-08). Four of these six have mitigations that are structural features of the methodology itself — the dual-route design (RISK-07), the uncertainty-aware calibration throughout (RISK-08), the co-located covariation campaign (RISK-05), and the RQ5 calibration criterion as a verifiable success condition (RISK-06) — rather than reactive controls to be applied if something goes wrong. One (RISK-01) is resolved by the pre-proposal PlanetScope access confirmation (RQ8). One (RISK-04) is mitigated by the AgroVIR farmer-access relationship and the non-destructive measurement protocol. The two medium-impact data-access risks (RISK-02, RISK-03) are addressable engineering challenges for which the literature provides established tools. No risk is simultaneously high probability and high impact without a credible mitigation.

Ethics Self-Assessment

Two ethics dimensions are active in this project. ETH-01 (Artificial Intelligence, application form ethics Category 8): the uncertainty-aware decision engine developed in WP2 and delivered in D2-01 constitutes an AI-based system that provides irrigation scheduling recommendations. The project addresses the associated ethical considerations through the probabilistic framing — the system presents recommendations together with their uncertainty rather than as deterministic commands — and through the explicit TRL 3–4 scoping that prevents premature deployment in operational contexts where AI-recommendation risks to farmer livelihoods could arise. The project operates within an exclusive civil application focus; no dual-use concerns arise. ETH-02 (Environmental and field activities, application form ethics Category 7): WP3 field validation involves measurement campaigns on agricultural land at AgroVIR-accessed Hungarian tomato farms. All measurement methods are non-destructive physiological techniques (chlorophyll fluorescence, stomatal conductance, canopy and leaf temperature, spectral reflectance); no adverse environmental, health, or safety implications arise. No human-subjects research, no vertebrate animal research, and no restricted materials are involved. Eötvös Loránd University (ELTE), Budapest, as a higher education establishment in an EU Member State, is required to have a gender equality plan in place at grant signature and throughout the fellowship.

Management Structure

Project governance is structured around two bodies appropriate for a single-researcher, single-beneficiary fellowship. The Fellowship Management Committee, composed of Dr. Rositsa Cholakova and Dr. András Jung, meets monthly and holds decision scope over: strategic oversight of fellowship progress, review of milestone achievement, approval of changes to the Career Development Plan, and resolution of issues beyond day-to-day research coordination. Monthly meetings are proportionate for a 24-month fellowship with five active work packages and at least one growing season of field campaigns. Matters unresolved at Fellowship Management Committee level are escalated to the Host Institutional Support Interface — Eötvös Loránd University (ELTE), Faculty of Informatics, Institute of Cartography and Geoinformatics — which, as the sole beneficiary legal entity and grant agreement signatory, is the final institutional authority for all grant-level obligations, including financial management, reporting to the European Commission, and institutional policy compliance.
