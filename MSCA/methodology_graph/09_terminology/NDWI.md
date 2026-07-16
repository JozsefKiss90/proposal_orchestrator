---
id: METH-TERM-024
title: "NDWI"
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
  - "[[NDMI]]"
  - "[[Sentinel 2]]"
  - "[[Crop Water Stress]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - Normalized Difference Water Index
tags:
  - methodology-graph
  - terminology
---

# NDWI

An optical water-content index derived from Sentinel-2 imagery.

## Definition / What it is

NDWI (Normalized Difference Water Index) is a remote-sensing index sensitive to vegetation and surface water content, computed from optical reflectance. It is one of the [[Sentinel 2]] optical vegetation indices the methodology lists alongside [[NDVI]] and [[NDMI]] (prompt.txt §3). The literature review describes how the spectral sensitivity of optical indices (NDVI/NDWI/NDMI), combined with all-weather SAR, improves detection of soil moisture, crop growth, and drought (litreview Report A §3.1).

## Role in this methodology

Because it tracks water content, NDWI is a particularly relevant [[Covariate]] for diagnosing [[Crop Water Stress]] — the plant condition when water supply is insufficient for demand. It works in concert with [[NDVI]] (greenness) and [[NDMI]] (moisture) as complementary optical channels in the field-state diagnosis. Like all optical indices it is constrained by cloud cover (litreview Report A §3.4), motivating its fusion with radar signals.

## Related

[[NDVI]] · [[NDMI]] · [[Sentinel 2]] · [[Crop Water Stress]] · [[Covariate]]
