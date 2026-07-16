---
id: METH-SOTA-001
title: "State of the Art - Multi Sensor Crop Water Stress Monitoring"
node_type: state_of_the_art
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
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "litreview Report A (literature_review.pdf pp.1-8), §3.1-3.4, Fig.4, Fig.5, Fig.6"
  - "prompt.txt §1, §8, §9"
evidence_strength: source_grounded
confidence: high
maturity: validated_in_literature
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes:
  - "[[Sentinel 1 and Sentinel 2 Integration]]"
  - "[[PlanetScope Usage Gap]]"
  - "[[Meteorological and Soil Sensor Integration]]"
  - "[[Operational Decision Support Gap]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Research Gap Matrix]]"
related_nodes:
  - "[[Core Architecture]]"
  - "[[Earth Observation Layer]]"
key_terms:
  - "[[SAR]]"
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[PlanetScope]]"
  - "[[Data Fusion]]"
  - "[[Multimodal Fusion]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "SOTA Hub"
  - "State of the Art"
tags:
  - methodology-graph
  - state-of-the-art
---

# State of the Art - Multi Sensor Crop Water Stress Monitoring

Hub node summarising what the published literature has established about combining satellite, meteorological and soil-sensor data for drought-stress monitoring and irrigation optimisation in row crops, and where the open scientific gaps remain.

This page synthesises **Report A** of `[[Source - Literature Review]]` — *"Combining Sentinel-1, Sentinel-2, PlanetScope, Meteorological Data, and Soil Sensors for Drought Stress Monitoring and Irrigation Optimization in Row Crops: State of the Research and Scientific Gaps"* (Consensus.app). The report screened a large body of literature (its method text states 20,233 papers initially identified, 168 screened, **top 50 included**; the flow figure separately cites 4.3M retrieved / 1.7K eligible / 50 included) to map current practice and the gaps this project would target.

## What the literature establishes

> [!note] Headline
> Multi-sensor integration — Sentinel-1 (SAR), Sentinel-2 (optical), PlanetScope, meteorological data and soil sensors — is a promising and increasingly common approach for monitoring drought stress and optimising irrigation in row crops, but **few studies achieve full integration across all sensor types at scale**, and operational, real-time decision support remains rare.

- **Dual-sensor is standard practice.** Most studies integrate two or three data types, commonly `[[SAR]]` Sentinel-1 plus Sentinel-2 optical indices, to track soil moisture, crop growth, irrigation events and drought. See `[[Sentinel 1 and Sentinel 2 Integration]]` (rated **Strong** evidence in Report A's claims table).
- **Meteorology and soil sensors add value.** ERA5-Land and in-situ soil moisture improve ETc, irrigation water requirement and root-zone moisture estimates; hybrid physical–ML models beat physical-only baselines. See `[[Meteorological and Soil Sensor Integration]]` (**Moderate**).
- **PlanetScope is under-used.** Its high spatial resolution is valuable, especially fused with `[[Sentinel 2]]`, but **few** studies combine it with both radar and ground sensors for row-crop drought/irrigation. See `[[PlanetScope Usage Gap]]` (**Moderate**).
- **Operational, all-sensor real-time decision support is scarce.** Few frameworks fuse every sensor type into a working real-time decision-support tool. See `[[Operational Decision Support Gap]]` (**Moderate**).

The `[[Research Gap Matrix]]` (Report A, Figure 6) quantifies these patterns as study counts, with the **Real-Time Decision Support × PlanetScope** cell labelled an explicit **GAP**.

## Methodological advances and persistent limitations

Report A §3.4 notes advances in machine learning for fusion (Random Forests, SVM, Deep Learning), vegetation-suppression techniques for soil-moisture retrieval, and near-real-time pipelines via Google Earth Engine. Persistent challenges it lists: **dense vegetation reduces SAR retrieval accuracy; cloud cover limits optical data; sensor calibration/integration complexity; and few studies achieve full integration across all desired sensor types at scale.** Top contributing authors identified are **N. Baghdadi, M. Zribi and S. Ferrant**; leading journals are *Remote Sensing*, *Agricultural Water Management* and *Water*.

## Role in this methodology

This SOTA hub anchors the project's novelty argument. The literature confirms the *building blocks* (multi-sensor fusion) are mature, while leaving the *combination this project proposes* — direct probabilistic fusion feeding an irrigation decision engine — open. That combination is argued in `[[Probabilistic Fusion Novelty Claim]]` (drawing additionally on Report B and `[[Source - Methodology Synthesis Prompt]]` §9) and realised in `[[Core Architecture]]`. The sensor families catalogued here map onto the project's `[[Earth Observation Layer]]`.

## Links and relationships

Children: `[[Sentinel 1 and Sentinel 2 Integration]]`, `[[PlanetScope Usage Gap]]`, `[[Meteorological and Soil Sensor Integration]]`, `[[Operational Decision Support Gap]]`, `[[Probabilistic Fusion Novelty Claim]]`, `[[Research Gap Matrix]]`. Parent hub: `[[Methodology Graph - Meta Node]]`.
