---
id: METH-ROUTE-001
title: "Route A - Direct Probabilistic Fusion"
node_type: methodology_route
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
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "methodology_idea.txt (the hardcore route: satellite as one more input into a probabilistic ML model — BHM or GP — straight to field state with uncertainty; one step instead of two; leans on ML)"
  - "prompt.txt §3 (Route 1 inputs, hidden-state list, models; rigorous but demanding)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes:
  - "[[Downscaling Critique]]"
  - "[[Diagnostic Branch]]"
downstream_nodes:
  - "[[AquaCrop Decision Interface]]"
related_nodes:
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Route Comparison]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Probabilistic Modelling Runtime]]"
  - "[[Model Complexity Risks]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Multimodal Fusion]]"
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Latent Field State]]"
  - "[[Posterior Distribution]]"
  - "[[Uncertainty Propagation]]"
  - "[[Covariate]]"
  - "[[SAR]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[PlanetScope]]"
  - "[[Root Zone Soil Moisture]]"
  - "[[Crop Water Stress]]"
risks:
  - "[[Model Complexity Risks]]"
open_questions:
  - "Will Route A be the main route or one of two implemented routes? (RQ2)"
  - "What exactly is the target field state estimated by the fusion model? (RQ3)"
validation_needs:
  - "Strong modelling expertise, good validation data, careful compute (per sources)"
aliases:
  - "Route 1"
  - "Hardcore route"
tags:
  - methodology-graph
  - route
---

# Route A - Direct Probabilistic Fusion

The "hardcore" route: feed the satellite as just one more input into a probabilistic model that takes all signals together and goes straight to the field state with its uncertainty — one step instead of two.

## What it is

Route A is the rigorous response to the [[Sub Pixel Problem]] and the direct embodiment of the [[Downscaling Critique]]'s one-step principle. Rather than reconstructing a fine pixel first, the satellite enters a **probabilistic machine-learning model** as one more [[Covariate]] alongside the other signals. As the design narrative puts it, the model "takes the satellite, the sensors, the soil and the weather together and goes straight to the field state with its uncertainty. One step instead of two, the covariates doing their work directly, with no intermediate pixel to inflate the error."

This is [[Data Fusion]] / [[Multimodal Fusion]] in service of estimating the [[Latent Field State]], returning not a point estimate but a full [[Posterior Distribution]] — keeping [[Uncertainty Propagation]] honest from the very first stage.

## Inputs (per prompt.txt §3)

| Group | Signals |
|---|---|
| Radar | [[Sentinel 1]] [[SAR]] — works through cloud, sensitive to surface structure/moisture |
| Optical | [[Sentinel 2]] — NDVI/NDWI/NDMI |
| High-res optical | [[PlanetScope]] — higher resolution for small fields, if available |
| Weather | rainfall, temperature, ET, radiation, wind |
| Soil sensors | moisture, temperature, conductivity |
| Field observations | crop type, growth stage, irrigation logs, yield, biomass, visual stress |

## Estimated hidden state (per prompt.txt §3)

The fusion model estimates the **hidden / latent state**: [[Root Zone Soil Moisture]], plant [[Crop Water Stress]], canopy development, biomass, and expected yield — each with an associated uncertainty range.

## Candidate models

The sources name three families, all probabilistic so they "return distributions/intervals":

- [[Bayesian Hierarchical Model]] — field-level effects plus general crop/soil/weather relationships, with explicit uncertainty.
- [[Gaussian Process]] — spatial / spatio-temporal prediction giving a value-plus-uncertainty surface.
- [[Probabilistic Machine Learning]] more broadly — any ML returning distributions rather than point predictions.

## Role in this methodology

Route A sits downstream of the [[Diagnostic Branch]] and the [[Downscaling Critique]], and feeds its probabilistic field-state estimate into the [[AquaCrop Decision Interface]], where it drives counterfactual irrigation simulation. It is the rigorous counterpart to [[Route B - Homogeneous Patch Proxy]]; the two are weighed in [[Route Comparison]]. Route A is also the methodological core behind the [[Probabilistic Fusion Novelty Claim]]: directly fusing multi-source data into probabilistic crop-water-state estimates is the part of the work that the literature reports as underdeveloped.

## Cost and difficulty

The narrative is candid that this is "the harder road, since it leans heavily on the machine learning side — the kind of thing that wants strong hands." The analyst synthesis adds that it is "rigorous but demanding," needing strong modelling expertise, good validation data, and careful compute — captured in [[Model Complexity Risks]] and supported by the [[Probabilistic Modelling Runtime]] infrastructure.

## Source grounding & open questions

All inputs, hidden-state variables, and model families above are drawn from `methodology_idea.txt` and `prompt.txt §3`; no numbers, crops, or partners are asserted beyond them. Whether Route A is the sole main route or one of two implemented routes is a project decision (RQ2, see [[Route Comparison]]), and the precise definition of the target field state is open (RQ3).
