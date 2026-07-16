---
id: METH-TERM-023
title: "NDVI"
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
  - "[[Source - Literature Review]]"
evidence_basis:
  - "prompt.txt §3 (Sentinel-2 optical: NDVI/NDWI/NDMI)"
  - "litreview Report A §3.1 (optical indices NDVI/NDWI/NDMI)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes: []
key_terms:
  - "[[Sentinel 2]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
  - "[[Multimodal Fusion]]"
  - "[[Covariate]]"
  - "[[Crop Water Stress]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - Normalized Difference Vegetation Index
tags:
  - methodology-graph
  - terminology
---

# NDVI

An optical vegetation-greenness index derived from Sentinel-2 imagery.

## Definition / What it is

NDVI (Normalized Difference Vegetation Index) is a remote-sensing index that summarises vegetation greenness and vigour from optical reflectance. In this methodology it is one of the [[Sentinel 2]] optical vegetation indices listed alongside [[NDWI]] and [[NDMI]] (prompt.txt §3). The literature review describes how studies leverage the spectral sensitivity of optical indices (NDVI/NDWI/NDMI) — combined with the all-weather capability of SAR — to improve detection of soil-moisture dynamics, crop growth, and drought (litreview Report A §3.1).

## Role in this methodology

NDVI is a [[Covariate]] feeding the probabilistic fusion of signals. As an optical channel it participates in [[Multimodal Fusion]] — combining radar, optical, sensor, and weather data — and contributes to estimating [[Crop Water Stress]] as part of the field-state diagnosis. Because optical indices are limited by cloud cover (litreview Report A §3.4), NDVI is typically paired with radar for robustness rather than used alone.

## Related

[[Sentinel 2]] · [[NDWI]] · [[NDMI]] · [[Multimodal Fusion]] · [[Covariate]] · [[Crop Water Stress]]
