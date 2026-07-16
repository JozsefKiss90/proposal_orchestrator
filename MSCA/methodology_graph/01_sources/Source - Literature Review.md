---
id: METH-SRC-001
title: "Source - Literature Review"
node_type: source
status: draft
version: 0.1
created: 2026-06-19
updated: 2026-06-19
domain:
  - crop_water_stress
  - irrigation_decision_support
project_scope:
  - methodology
  - proposal_development
source_refs:
  - "[[Source - Literature Review]]"
evidence_basis:
  - "sources/literature_review.pdf pp.1-12"
  - "litreview Report A (pp.1-8)"
  - "litreview Report A Fig.5 (Claims & Evidence table)"
  - "litreview Report A Fig.6 (Research gap matrix)"
  - "litreview Report B (pp.9-12)"
evidence_strength: source_grounded
confidence: high
maturity: validated_in_literature
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes:
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Research Gap Matrix]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
related_nodes:
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Research Gap Matrix]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Methodology Graph - Meta Node]]"
  - "[[Source Traceability Register]]"
key_terms:
  - "[[SAR]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[PlanetScope]]"
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
  - "[[Data Fusion]]"
  - "[[Multimodal Fusion]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "literature_review.pdf"
  - "Consensus Literature Review"
tags:
  - methodology-graph
  - source
---

# Source - Literature Review

> [!note] Immutable source note
> This node is a faithful summary of the raw source `sources/literature_review.pdf` (12 pp). The raw file is immutable per the Karpathy LLM-wiki rules ([[Source - LLM Wiki Method]]); this page restates it **with attribution** and never as un-cited fact.

One-line summary: a two-part AI-assisted literature review (Consensus.app) establishing that **dual-sensor Sentinel-1 + Sentinel-2 fusion is mature practice**, that **full integration including PlanetScope, soil sensors and meteorology into real-time decision support is rare**, and that **explicit probabilistic row-crop drought/irrigation frameworks remain underdeveloped** — leaving room for genuine novelty.

The PDF bundles **two Consensus reports**: **Report A** (pp.1-8) = state of research & scientific gaps; **Report B** (pp.9-12) = the probabilistic novelty-gap question. It is the empirical backbone for the [[State of the Art - Multi Sensor Crop Water Stress Monitoring]] hub, the [[Research Gap Matrix]], and the [[Probabilistic Fusion Novelty Claim]].

## Report A — State of the Research & Scientific Gaps

**Title:** *"Combining Sentinel-1, Sentinel-2, PlanetScope, Meteorological Data, and Soil Sensors for Drought Stress Monitoring and Irrigation Optimization in Row Crops: State of the Research and Scientific Gaps."*
**Engine / method:** Consensus.app AI literature search. Methods text reports **20,233 papers identified** through initial queries → **168 unique papers screened** → **top 50 included**. The flow figure (Fig.2) separately cites **4.3M retrieved → 1.7K eligible → 50 included** (21 searches + 1 citation-graph use).

**Current practice (§3.1):** most studies integrate **2-3 data types**, most commonly **[[Sentinel 1]] [[SAR]] + [[Sentinel 2]] optical** ([[NDVI]]/[[NDWI]]/[[NDMI]]), to monitor soil moisture, crop growth, irrigation events and drought. SAR's all-weather capability plus optical spectral richness improves detection; some studies add meteorology (precipitation, ET) or in-situ soil moisture to calibrate/validate.

**PlanetScope (§3.2):** high spatial resolution is valuable (especially fused with [[Sentinel 2]]), but **few** studies combine [[PlanetScope]] with **both** radar ([[Sentinel 1]]) **and** ground sensors for drought/irrigation in row crops — see [[PlanetScope Usage Gap]]. PlanetScope is mostly used for yield estimation / land cover, not direct plant-based drought monitoring.

**Meteo & soil (§3.3):** ERA5-Land + in-situ soil moisture improve ETc / [[Irrigation Water Requirement]] / [[Root Zone Soil Moisture]] estimates; **hybrid physical-ML models outperform physical-only baselines** (Izquierdo-Sanz & Moltó 2026) — see [[Meteorological and Soil Sensor Integration]].

**Advances & limitations (§3.4):** ML (Random Forests / SVM / Deep Learning) for fusion; vegetation-suppression for soil moisture; near-real-time via Google Earth Engine. Persistent challenges: **dense vegetation reduces SAR retrieval accuracy; cloud cover limits optical; sensor calibration/integration is complex; few achieve full integration across all sensor types at scale.**

**Top contributors:** authors **N. Baghdadi, M. Zribi, S. Ferrant**; journals *Remote Sensing*, *Agricultural Water Management*, *Water*.

### Claims & Evidence table (Fig.5)

| Claim | Evidence strength |
|---|---|
| Dual-sensor (S1+S2) > single-sensor for drought/irrigation monitoring | **Strong** |
| Adding meteorological & soil sensor data further enhances performance | Moderate |
| Full integration including PlanetScope is rare in row-crop research | Moderate |
| ML / data-fusion methods outperform physical-only models | Moderate |
| Dense vegetation/canopy reduces SAR retrieval accuracy | Moderate |
| Lack of operational frameworks unifying all sensors at scale for real-time decision support | Moderate (Duan 2025) |

### Research gap matrix (Fig.6)

| Topic / Outcome | Dual-Sentinel | + Meteorology | + Soil sensors | + PlanetScope |
|---|---|---|---|---|
| Drought Stress Detection | 18 | 10 | 7 | 3 |
| Irrigation Optimization | 15 | 9 | 6 | 2 |
| Real-Time Decision Support | 7 | 4 | 3 | **GAP** |

The empty **Real-Time Decision Support × PlanetScope** cell is the literature's clearest white space; it directly motivates the [[Operational Decision Support Gap]] and the [[Research Gap Matrix]] node.

**Open research questions (Report A):** full field-scale integration of S1/S2/PlanetScope/meteo/soil; optimal ML / data-fusion strategies for heterogeneous multi-source agricultural datasets; cost-effective ground-truth networks to validate large-scale multi-sensor frameworks.

### Report A reference DOIs (50 included; key entries)
Chun-Yang 2022 (10.3390/rs14051205); Abdelrahim & Jin 2025 (10.1007/s10661-025-13686-3); Amankulova 2024 (10.1016/j.asr.2024.01.040); Bousbih 2018 (10.3390/rs10121953); Chakhar 2024 (10.3390/rs16030458); Corbari 2022 (10.1080/22797254.2022.2084643); Duan 2025 (10.1109/jstars.2025.3580652); Elwan 2022 (10.3390/w14050804); Farmonov 2023 (10.1080/17538947.2023.2186505); Ferrant 2017 (10.3390/rs9111119); Gao 2018 (10.3390/rs10091495); Ghazaryan 2020 (10.1080/15481603.2020.1778332); Hamze 2023 (10.3390/rs15164081); Ibrahim 2023 (10.1007/s10661-023-11871-w); Ihuoma 2021 (10.1016/j.jag.2021.102396); Izquierdo-Sanz & Moltó 2026 (10.3390/agronomy16050541); Jędrejek & Pudełko 2023 (10.3390/agriculture13091798); Khabbazan 2019 (10.3390/rs11161887); Kpienbaareh 2021 (10.3390/rs13040700); Mkhwenkwana 2025 (10.1016/j.jag.2025.104647); Müller 2025 (10.1016/j.agrformet.2025.110789); Noory 2025 (10.1016/j.agwat.2024.109263); Pageot 2020 (10.3390/rs12183044); Wu 2024 (10.1016/j.agwat.2024.108718); Zhao 2025 (10.3390/rs17132130).

## Report B — Probabilistic Novelty Gap

**Question:** *"can this data fusion methodology be used in row crop probabilistic frameworks? what is the gap? will there be a novelty?"*
**Headline conclusion:** *"While multimodal data fusion is mature, probabilistic row-crop drought/irrigation frameworks remain underdeveloped, so a Bayesian/data-fusion approach can still be novel."*

Multi-source fusion (UAV, satellite, ground/IoT, weather) is widely used for crop status/yield but **rarely embedded in explicit probabilistic or decision-optimization frameworks** for row-crop drought stress and irrigation.

**Precedents that exist:** gated/deep multimodal fusion for yield/biomass (Mena 2024, Maimaitijiang 2020, Li 2025, Yewle 2025, Yang 2024, Fei 2022, Xian 2024); **Bayesian Maximum Entropy** drought-forecast fusion outputting PMFs of drought indices (Ghazipour & Mahjouri 2021, 10.1016/j.jenvman.2021.114245); multimodal drought-stress classification (MF-FusionNet, Guo 2025, 10.3390/agriculture15151639); **bivariate copula** drought↔irrigation scheduling with multiobjective optimization (Banibayat 2021, 10.1007/s40996-021-00589-9; Wang 2021 Copula-NSPSO, 10.1007/s11269-021-02981-6); **dynamic Bayesian networks** for crop water productivity / planting-structure optimization (Yantao/Xue 2024, 10.1038/s41598-024-68523-3); drought-loss-risk multisource fusion (Zhang M. 2021, 10.1007/s11069-021-05078-w); AIoT + LSTM watering DSS (Lin 2025, 10.1016/j.iot.2025.101617); data-assimilation + crop model + multiobjective optimization for cotton (Liu 2025, 10.1016/j.agwat.2025.109774); precision-irrigation DSS challenges for center pivots (Zhang J. 2021, 10.1088/1748-9326/abe436).

**Gaps / potential novelty:**
1. **Few** works couple *rich* multimodal fusion (deep/gated) **directly** with **explicit probabilistic outputs** (full predictive distributions) for row-crop drought stress or irrigation decision rules.
2. End-to-end **"fusion → probabilistic drought state → optimized irrigation" at sub-field resolution in row crops is not clearly reported** — existing optimization/crop-model works rely on calibrated process models and classical indices, not learned multimodal fusion layers.
3. **Uncertainty propagation** from fused observations into irrigation optimization is **still rare** (BME for drought indices is a strong precedent but not yet tied to high-resolution crop sensing).

**Conclusion:** a framework that (1) fuses multi-source crop/soil/weather/IoT data with a modern multimodal architecture, (2) outputs **explicit probabilistic drought-stress states at row/sub-field scale**, and (3) **links these to irrigation optimization** would meaningfully extend current work — **genuine research novelty**. This is the evidentiary core of the [[Probabilistic Fusion Novelty Claim]] and underpins [[Route A - Direct Probabilistic Fusion]].

## Role in this methodology

Report A grounds the **state-of-the-art** and the **gap** that the project targets; Report B grounds the **probabilistic novelty argument**. Together they justify the project's red thread of [[Uncertainty Propagation]] and the move from "monitoring dashboard" to a probabilistic decision framework. Downstream nodes — [[State of the Art - Multi Sensor Crop Water Stress Monitoring]], [[Research Gap Matrix]] and [[Probabilistic Fusion Novelty Claim]] — cite this source for their factual claims; the [[Source Traceability Register]] tracks that fan-out. Navigate up via the [[Methodology Graph - Meta Node]].

## Links & relationships
- **Feeds:** [[State of the Art - Multi Sensor Crop Water Stress Monitoring]], [[Research Gap Matrix]], [[Probabilistic Fusion Novelty Claim]]
- **Related:** [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]], [[Methodology Graph - Meta Node]], [[Source Traceability Register]]
- **Key terms:** [[SAR]], [[Sentinel 1]], [[Sentinel 2]], [[PlanetScope]], [[NDVI]], [[NDWI]], [[NDMI]], [[Data Fusion]], [[Multimodal Fusion]]
