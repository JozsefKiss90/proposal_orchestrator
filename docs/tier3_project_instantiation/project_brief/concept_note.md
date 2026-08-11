---
record_type: tier3_concept_note
authority: "CLAUDE.md §5 Tier 3, §12.2 status categories, §13.3 no fabricated project facts"
source: docs/tier3_project_instantiation/source_materials/part_b_draft_v0/FIELDWISE_MSCA_Master_Draft.docx
lift_record: docs/tier4_orchestration_state/decision_log/fieldwise-tier3-lift_2026-08-11.json
provenance_manifest: docs/tier3_project_instantiation/hand_lift_provenance.json
spine_status: confirmed_real
validation_status: Confirmed
source_ref: "Draft §1.1.1-§1.1.7, ¶21-79"
note: >
  Prose lifted verbatim from the draft with no rewriting (§10.5 traceability). Paragraph
  numbers ¶N follow the numbering scheme defined in hand_lift_provenance.json. List
  formatting reproduces the draft's own paragraph breaks; no sentence was added, merged
  or reworded.
---

# FIELDWISE — Concept note

<!-- source_ref: §1.1.1 ¶21-26 -->
## European challenge and scientific rationale

European agriculture is entering an increasingly water-constrained production environment. Approximately 30% of EU territory is affected by seasonal water scarcity in an average year, while climate change is expected to intensify drought frequency, severity and seasonal fluctuations in freshwater availability.

Agriculture is particularly exposed. Southern Europe accounts for a large share of EU agricultural water abstraction, while climate change is expected both to increase the agricultural area requiring irrigation and to increase irrigation demand in already irrigated areas. Water scarcity already translates into agricultural yield losses and higher water costs.

This creates a critical challenge for high-value horticultural field crops, for which inappropriate irrigation timing can affect productivity, fruit quality, water-use efficiency and economic return.

FIELDWISE will use processing tomato as its model crop. Processing tomato represents a particularly demanding system for predictive irrigation because crop productivity depends strongly on the temporal interaction between water availability, atmospheric demand, developmental stage and irrigation management.

Can developing crop water stress be identified early enough for irrigation management to prevent or reduce damaging physiological stress?

<!-- source_ref: §1.1.2 ¶27-35 -->
## The limitation of accuracy-centred agricultural AI

The rapid expansion of Earth Observation (EO), proximal sensing, IoT and machine learning (ML) has enabled increasingly sophisticated crop-monitoring systems. Yet agricultural ML remains predominantly evaluated through retrospective metrics such as R², RMSE, F1-score or classification accuracy.

A model may achieve impressive retrospective performance while being unsuitable for actual irrigation management.

- Observations from related seasons, plots or fields may occur in both training and testing datasets, producing optimistic performance estimates.
- A model may learn environment-specific relationships associated with a particular soil, cultivar, management regime or year rather than transferable crop-water relationships.
- Accurate identification of an already established stress condition may occur too late to modify the irrigation decision.
- Even a model that transfers between research experiments may fail when exposed to the heterogeneity and incomplete data encountered under commercial farming conditions.

FIELDWISE therefore proposes a fundamental shift from retrospective accuracy to prospective prediction, then to transferability, and finally to field-level decision value.

The best agricultural model is not necessarily the model with the highest retrospective accuracy. Operational value requires timeliness, calibration, transferability and decision value.

<!-- source_ref: §1.1.3 ¶36-49 -->
## Preliminary work: DrR - Digital Agronomist

FIELDWISE does not start from a purely conceptual technology base.

The researcher has already initiated DrR - Digital Agronomist, a desktop research prototype operating with data from a scientific experimental field. The prototype demonstrates the technical feasibility of integrating soil-sensor information, field meteorological-station observations and Sentinel-2A data within a common digital environment.

However, the prototype has not yet established:

- physiologically validated water-stress targets;
- prospective forecasting;
- uncertainty-aware predictions;
- cross-year robustness;
- cross-country transferability;
- research-to-commercial-field transferability;
- field-level irrigation decision value;
- operational FMIS interoperability.

The MSCA fellowship therefore does not simply fund conversion of an existing desktop program into a website. FIELDWISE provides the missing scientific validation and transferability framework required before the technology can credibly move toward operational use.

Pathway: DrR research prototype -> FIELDWISE scientific research -> validated predictive intelligence -> DrR - Digital Agronomist Web MVP -> AgroVIR farmer-field and implementation testing -> post-MSCA integration/exploitation pathway.

<!-- source_ref: §1.1.4 ¶50-62 -->
## Scientific gaps

**G1 - Physiological target gap**

Water stress is frequently defined through spectral proxies. FIELDWISE will define stress using physiologically meaningful plant responses rather than relying solely on vegetation-index thresholds.

**G2 - Sensor-domain gap**

The approximately five-year historical spectral archive available from MATE originates primarily from handheld hyperspectral measurements. FIELDWISE will explicitly investigate which proximal hyperspectral stress signatures can be transferred to Sentinel-2.

**G3 - Temporal gap**

Static observations poorly describe a dynamic stress process. FIELDWISE will model temporal trajectories and forecast future stress rather than only map current condition.

**G4 - Geographic transferability gap**

A model developed under MATE conditions in Hungary may learn site-specific relationships. FIELDWISE will transfer the model to MVCRI in Bulgaria as an independent cross-country test.

**G5 - Operational transferability gap**

Successful transfer between research environments does not prove readiness for commercial farming. AgroVIR will provide the research-to-farmer-field operational bridge.

**G6 - Decision-value gap**

Prediction performance does not automatically equal irrigation usefulness. FIELDWISE introduces Field Decision Value (FDV) as the final evaluation layer.

<!-- source_ref: §1.1.5 ¶63-64 -->
## Central research question

Can physiologically grounded crop water stress in high-value processing tomato be forecast early enough to support irrigation decisions, while maintaining reliable predictive performance as the model moves from historical experimental observations to unseen seasons, from Hungary to Bulgaria, and ultimately from research fields to commercial farming conditions?

<!-- source_ref: §1.1.6 ¶65-72 -->
## Research questions

- RQ1. Which hyperspectral, soil and meteorological variables provide the earliest reliable indication of developing physiological water stress in processing tomato?
- RQ2. Which hyperspectral stress signatures can be reproduced or approximated at Sentinel-2 spectral and spatial resolution?
- RQ3. How far in advance can physiologically meaningful stress be predicted while maintaining sufficient reliability for irrigation decisions?
- RQ4. Which predictive relationships remain stable across seasons and between Hungary and Bulgaria?
- RQ5. How much local information is required to adapt a Hungarian-trained model to a contrasting Bulgarian agro-environment?
- RQ6. Does the model remain useful when transferred from scientific experimental fields to farmer-managed commercial fields?
- RQ7. Does a model selected according to transferability, calibration and lead time provide greater field-level irrigation decision value than one selected primarily according to retrospective predictive accuracy?

<!-- source_ref: §1.1.7 ¶73-79 -->
## Hypotheses

- **H1 - Physiological early-warning hypothesis.** Changes in soil-water availability and atmospheric demand, combined with hyperspectral crop-response information, will identify developing water stress before substantial conventional canopy greenness deterioration occurs.
- **H2 - Sensor-transfer hypothesis.** A subset of physiologically meaningful hyperspectral features can be translated into Sentinel-compatible predictors through spectral resampling, concurrent proximal/satellite observations and scale-aware calibration.
- **H3 - Temporal-transfer hypothesis.** Performance on an unseen season will be lower than performance obtained through conventional random validation, revealing the extent of temporal generalisation.
- **H4 - Geographic-transfer hypothesis.** Model performance will decrease when transferred from MATE, Hungary to MVCRI, Bulgaria, but limited local calibration and/or hierarchical modelling will recover part of this performance loss.
- **H5 - Operational-transfer hypothesis.** Additional performance degradation will occur when transferring from controlled research environments to farmer-managed commercial fields, revealing which inputs and model components are sufficiently robust for operational use.
- **H6 - Decision-value hypothesis.** The model achieving the highest retrospective predictive accuracy will not necessarily provide the greatest irrigation decision value because warning lead time, calibration and false/missed interventions also determine usefulness.
