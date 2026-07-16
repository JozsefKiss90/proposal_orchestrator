---
id: METH-INFRA-003
title: "Ground Sensing Layer"
node_type: infrastructure_layer
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
  - "[[Source - Methodology Synthesis Prompt]]"
  - "[[Source - Literature Review]]"
evidence_basis:
  - "prompt.txt §8 (Ground sensing: soil-moisture sensors, weather station/meteo, irrigation logs, crop observations)"
  - "prompt.txt §3 (soil sensors: in-situ soil moisture, temperature, possibly conductivity; field observations: crop type, growth stage, irrigation logs, yield, biomass, visual stress)"
  - "litreview Report A §3.3 (in-situ soil moisture improves ETc/IWR/root-zone moisture)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes:
  - "[[Geospatial and Time Series Data Platform]]"
related_nodes:
  - "[[Meteorological and Soil Sensor Integration]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Control Stand Variant]]"
key_terms:
  - "[[Root Zone Soil Moisture]]"
  - "[[Ground Truth]]"
risks: []
open_questions:
  - "What ground-truth measurements will be collected? (RQ4)"
validation_needs:
  - "Sensor calibration and cross-comparison; density of the ground-truth network"
aliases:
  - "In-situ sensing layer"
tags:
  - methodology-graph
  - infrastructure
---

# Ground Sensing Layer

The in-situ infrastructure layer: soil-moisture sensors, on-site weather/meteo data, irrigation logs and crop observations that anchor the satellite signals to real field measurements.

## What it is

Per the analyst synthesis (prompt.txt §8), the ground-sensing layer comprises: **soil-moisture sensors, weather station / meteo data, irrigation logs, and crop observations**. It is the in-situ counterpart to the [[Earth Observation Layer]] within the [[Infrastructure Architecture]] and a primary source of [[Ground Truth]].

## Components and their role

- **Soil-moisture sensors** — in-situ soil moisture and temperature, possibly also conductivity (prompt.txt §3). These directly inform **[[Root Zone Soil Moisture]]**, a key diagnostic state variable. The literature review notes that in-situ soil moisture (with ERA5-Land) improves estimates of ETc, irrigation water requirement and root-zone moisture (litreview Report A §3.3); see [[Meteorological and Soil Sensor Integration]].
- **Weather station / meteo data** — on-site meteorological observations. (The fuller weather/climate inputs and the future weather ensembles are treated in [[Weather and Climate Data Layer]].)
- **Irrigation logs** — records of irrigation events; both an input and a means of validating detected irrigation.
- **Crop observations** — field observations including crop type, growth stage, irrigation logs, yield, biomass, and visual stress observations (prompt.txt §3).

## Role in this methodology

This layer supplies the **[[Ground Truth]]** used to train and validate the diagnosis, and the in-situ soil-water variables that complement the satellite covariates. It is especially central to **[[Route B - Homogeneous Patch Proxy]]** and its experimental **[[Control Stand Variant]]**: those routes depend on physically observing a nearby homogeneous patch (or a deliberately planted control stand) and measuring whether its response covaries with the target crop — which requires exactly the kind of in-situ sensing and crop observation this layer provides.

> [!note] Why ground truth is pivotal
> The methodology's "hardcore" route (Route A) is described as demanding precisely because it **needs good validation data**. Dense, well-calibrated ground sensing underpins both the training of the probabilistic models and the later uncertainty calibration in the validation layer.

## Source grounding

Layer composition: prompt.txt §8. Sensor and observation details: prompt.txt §3. Soil-moisture value for ETc/IWR/root-zone moisture: litreview Report A §3.3. The literature also flags that **few efforts achieve large-scale validation with dense ground-truth networks**, and that **sensor calibration/integration complexity** is a persistent challenge (litreview Report A §3.4 and key limitations).

## Open questions

> [!warning] Ground-truth protocol open
> **What ground-truth measurements will be collected** is an open question (RQ4); the depth and density of the ground-truth network is a known limitation in the literature. The validation specifics live in [[Validation and Field Trial Layer]].

## Links & relationships

Up to [[Infrastructure Architecture]]; feeds [[Geospatial and Time Series Data Platform]]. State-of-the-art context in [[Meteorological and Soil Sensor Integration]]; methodological use in [[Route B - Homogeneous Patch Proxy]] and [[Control Stand Variant]]. Key terms: [[Root Zone Soil Moisture]], [[Ground Truth]].
