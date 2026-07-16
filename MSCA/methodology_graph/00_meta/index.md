---
id: METH-META-002
title: "index"
node_type: meta
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
  - "[[Source - LLM Wiki Method]]"
evidence_basis:
  - "Build brief §D, §E (node registry)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[Methodology Graph Dashboard]]"
  - "[[Source Traceability Register]]"
key_terms: []
risks: []
open_questions:
  - "[[Ten Research Questions]]"
validation_needs: []
aliases:
  - "Map of Content"
  - "Graph Index"
tags:
  - methodology-graph
  - meta
---

# index

Map-of-Content for the methodology knowledge graph. Every canonical node grouped by category. Up to the [[Methodology Graph - Meta Node]]; for live tables see [[Methodology Graph Dashboard]].

## Meta & governance

- [[Methodology Graph - Meta Node]]
- [[log]]
- [[Methodology Graph Schema]]
- [[Graph Maintenance Rules]]
- [[Source Traceability Register]]
- [[Methodology Graph Dashboard]]

## Sources

- [[Source - Literature Review]]
- [[Source - Methodology Idea]]
- [[Source - Methodology Synthesis Prompt]]
- [[Source - LLM Wiki Method]]

## Core architecture

- [[Core Architecture]]
- [[Diagnostic Branch]]
- [[Prognostic Branch]]
- [[Uncertainty Chain]]
- [[Observation to Decision Pipeline]]

## State of the art

- [[State of the Art - Multi Sensor Crop Water Stress Monitoring]]
- [[Sentinel 1 and Sentinel 2 Integration]]
- [[PlanetScope Usage Gap]]
- [[Meteorological and Soil Sensor Integration]]
- [[Operational Decision Support Gap]]
- [[Probabilistic Fusion Novelty Claim]]
- [[Research Gap Matrix]]

## Methodological routes

- [[Sub Pixel Problem]]
- [[Downscaling Critique]]
- [[Route A - Direct Probabilistic Fusion]]
- [[Route B - Homogeneous Patch Proxy]]
- [[Control Stand Variant]]
- [[Route Comparison]]

## Decision framework

- [[AquaCrop Decision Interface]]
- [[Uncertainty Aware AquaCrop Calibration]]
- [[Counterfactual Irrigation Simulation]]
- [[Weather Ensemble Scenario Evaluation]]
- [[Profit Based Objective Function]]
- [[Decision Recommendation Logic]]

## Infrastructure

- [[Infrastructure Architecture]]
- [[Earth Observation Layer]]
- [[Ground Sensing Layer]]
- [[Weather and Climate Data Layer]]
- [[Geospatial and Time Series Data Platform]]
- [[Probabilistic Modelling Runtime]]
- [[AquaCrop Simulation Runtime]]
- [[Decision Engine Layer]]
- [[Validation and Field Trial Layer]]
- [[Web MVP and User Interface Layer]]

## Risks & SWOT

- [[Methodology SWOT Matrix]]
- [[Risk Register]]
- [[Validation Risks]]
- [[Data Access Risks]]
- [[Model Complexity Risks]]
- [[Operationalisation Risks]]

## Partners

- [[Partner Roles Overview]]
- [[ELTE Role]]
- [[PI Role]]
- [[Methodology Contributor Role]]
- [[AgroVIR Validation Partner Role]]
- [[Unconfirmed Partner Placeholders]]

## Research questions

- [[Ten Research Questions]]

## Terminology

- [[Data Fusion]] · [[Multimodal Fusion]] · [[Ground Truth]] · [[Covariate]] · [[Downscaling]] · [[Cokriging]]
- [[Bayesian Hierarchical Model]] · [[Gaussian Process]] · [[Probabilistic Machine Learning]]
- [[Latent Field State]] · [[Posterior Distribution]] · [[Uncertainty Propagation]]
- [[Counterfactual Simulation]] · [[Weather Ensemble]] · [[AquaCrop]]
- [[Expected Profit]] · [[Expected Utility]] · [[Decision Regret]]
- [[Root Zone Soil Moisture]] · [[Crop Water Stress]] · [[Irrigation Water Requirement]] · [[Evapotranspiration]]
- [[NDVI]] · [[NDWI]] · [[NDMI]] · [[SAR]] · [[PlanetScope]] · [[Sentinel 1]] · [[Sentinel 2]]

## Live list of all graph nodes

```dataview
LIST
FROM #methodology-graph
SORT id ASC
```

```dataview
TABLE node_type, evidence_strength, confidence, maturity
FROM #methodology-graph
WHERE node_type != "dashboard"
SORT node_type, id
```
