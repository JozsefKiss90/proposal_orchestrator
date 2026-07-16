---
id: METH-TERM-025
title: "NDMI"
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
  - "[[NDVI]]"
  - "[[NDWI]]"
  - "[[Sentinel 2]]"
  - "[[Crop Water Stress]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - Normalized Difference Moisture Index
tags:
  - methodology-graph
  - terminology
---

# NDMI

An optical moisture index derived from Sentinel-2 imagery.

## Definition / What it is

NDMI (Normalized Difference Moisture Index) is a remote-sensing index sensitive to vegetation moisture content, computed from optical reflectance. It is the third of the [[Sentinel 2]] optical vegetation indices the methodology lists alongside [[NDVI]] and [[NDWI]] (prompt.txt §3). The literature review describes how the spectral sensitivity of these optical indices (NDVI/NDWI/NDMI), combined with the all-weather capability of SAR, improves detection of soil-moisture dynamics, crop growth, and drought (litreview Report A §3.1).

## Role in this methodology

NDMI contributes a moisture-sensitive optical signal to the diagnosis of [[Crop Water Stress]], complementing [[NDVI]] (greenness) and [[NDWI]] (water content). As a [[Covariate]] it is fused with radar, soil, and weather signals rather than used in isolation, since cloud cover limits optical availability (litreview Report A §3.4).

## Related

[[NDVI]] · [[NDWI]] · [[Sentinel 2]] · [[Crop Water Stress]] · [[Covariate]]
