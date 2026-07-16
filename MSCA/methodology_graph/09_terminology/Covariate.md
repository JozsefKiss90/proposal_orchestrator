---
id: METH-TERM-004
title: "Covariate"
node_type: concept
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
  - "[[Source - Methodology Idea]]"
evidence_basis:
  - "prompt.txt §7 (terminology)"
  - "prompt.txt §2 (covariates + uncertainty → prediction directly)"
  - "methodology_idea.txt (covariates and their uncertainty used directly, in one step)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Sub Pixel Problem]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Downscaling]]"
  - "[[Cokriging]]"
  - "[[NDVI]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Explanatory variable"
  - "Predictor"
tags:
  - methodology-graph
  - terminology
---

# Covariate

**Covariate** is an explanatory input variable used to predict an outcome — for example [[NDVI]], rainfall, soil type or temperature ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
A covariate is any measured quantity the model uses as an input to explain or predict the target. In this project the covariates are the fused signals: optical indices, radar backscatter, weather variables and soil-sensor readings (see [[Data Fusion]]).

## Role in this methodology
Covariates are central to the project's key methodological argument. The standard [[Downscaling]] approach uses covariates to first manufacture a fine pixel (e.g. by [[Cokriging]]) and only then predicts the outcome. The PI's narrative rejects that detour: the covariates and *their uncertainty* can be used **directly** for the prediction, in one step, with no intermediate pixel to inflate the error ([[Source - Methodology Idea]]; [[Source - Methodology Synthesis Prompt]] §2). This is exactly how [[Route A - Direct Probabilistic Fusion]] treats every input — as a covariate fed straight to the field state with its uncertainty.

Because a small horticultural plot is sub-pixel, covariates are what let the system bypass the [[Sub Pixel Problem]] rather than pretend an estimated pixel was observed.

## Related
[[Data Fusion]] · [[Downscaling]] · [[Cokriging]] · [[NDVI]] · [[Route A - Direct Probabilistic Fusion]] · [[Sub Pixel Problem]]
