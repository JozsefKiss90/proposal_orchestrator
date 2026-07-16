---
id: METH-INFRA-004
title: "Weather and Climate Data Layer"
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
  - "prompt.txt §3 (weather: rainfall, temperature, evapotranspiration, radiation, wind)"
  - "prompt.txt §6 (run each decision under multiple possible weather futures)"
  - "prompt.txt §8 (weather station/meteo data as an infrastructure component)"
  - "litreview Report A §3.3 (ERA5-Land + in-situ soil moisture improve ETc/IWR/root-zone moisture)"
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
  - "[[Weather Ensemble Scenario Evaluation]]"
  - "[[Meteorological and Soil Sensor Integration]]"
key_terms:
  - "[[Weather Ensemble]]"
  - "[[Evapotranspiration]]"
risks: []
open_questions:
  - "Source(s) and provider(s) of operational weather-ensemble forecasts (provider unconfirmed)"
validation_needs:
  - "Harmonising reanalysis (ERA5-Land) with on-site weather observations"
aliases:
  - "Weather data layer"
  - "Meteorological data layer"
tags:
  - methodology-graph
  - infrastructure
---

# Weather and Climate Data Layer

The meteorological infrastructure layer: historical and current weather variables plus the forward-looking **weather ensembles** that drive counterfactual irrigation simulations.

## What it is

This layer supplies the weather and climate inputs the methodology consumes. The analyst synthesis lists the weather variables as **rainfall, temperature, evapotranspiration, radiation and wind** (prompt.txt §3), and places weather station / meteo data inside the infrastructure stack (prompt.txt §8). The literature review adds **ERA5-Land** reanalysis, which (with in-situ soil moisture) improves estimates of ETc, irrigation water requirement and root-zone moisture (litreview Report A §3.3).

> [!note] Why a separate layer
> prompt.txt §8 groups meteo data under the ground-sensing row. Splitting weather/climate into its own canonical node is *(proposal synthesis)*: the weather inputs serve two distinct functions — historical/current covariates for diagnosis, and **forward-looking ensembles** for the prognostic decision step — that warrant separate treatment. The underlying components are all source-grounded.

## Two functions

1. **Diagnostic inputs (now/past).** Rainfall, temperature, [[Evapotranspiration]], radiation and wind act as covariates feeding the field-state diagnosis, and combine with in-situ soil moisture to improve water-balance estimates (litreview Report A §3.3). See [[Meteorological and Soil Sensor Integration]].
2. **Prognostic futures.** The decision principle is counterfactual: each candidate irrigation decision is run **under multiple possible weather futures** (prompt.txt §6). This layer therefore supplies the **[[Weather Ensemble]]** — multiple plausible future weather paths — consumed by [[Weather Ensemble Scenario Evaluation]].

## Role in this methodology

Weather data is what makes the prognostic branch honest about the future: rather than assume a single deterministic forecast, the method evaluates each decision across an ensemble of weather paths and aggregates the expected outcome. This carries weather uncertainty into the decision, in keeping with the project's "red thread" of end-to-end uncertainty. The [[Evapotranspiration]] term links this layer to AquaCrop, the crop model that is especially suited where water is limiting.

## Source grounding

Weather variables: prompt.txt §3. Use of weather futures in the decision step: prompt.txt §6. ERA5-Land and the water-balance benefit: litreview Report A §3.3. Infrastructure placement of meteo data: prompt.txt §8.

## Open questions

> [!warning] Forecast provider unconfirmed
> The sources establish *that* weather ensembles are used, but **no specific operational weather-forecast or ensemble provider is named**. Do not assume a particular provider. confidence: low on the specific data source for forward ensembles.

## Links & relationships

Up to [[Infrastructure Architecture]]; feeds [[Geospatial and Time Series Data Platform]]. Drives [[Weather Ensemble Scenario Evaluation]]; complements [[Meteorological and Soil Sensor Integration]]. Key terms: [[Weather Ensemble]], [[Evapotranspiration]].
