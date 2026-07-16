---
id: METH-TERM-029
title: "Sentinel 2"
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
  - "litreview Report A §3.1 (S1 SAR + S2 optical), §4 Discussion (dual-sensor standard practice)"
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
  - "[[NDMI]]"
  - "[[Sentinel 1]]"
  - "[[Earth Observation Layer]]"
  - "[[Sentinel 1 and Sentinel 2 Integration]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - S2
  - Sentinel-2
tags:
  - methodology-graph
  - terminology
---

# Sentinel 2

The Copernicus optical satellite — source of vegetation indices NDVI, NDWI, and NDMI.

## Definition / What it is

Sentinel 2 is the optical satellite in the Copernicus programme. In this methodology it supplies optical vegetation indices — [[NDVI]], [[NDWI]], and [[NDMI]] (prompt.txt §3). The literature review reports that most studies integrate Sentinel-1 SAR with Sentinel-2 optical imagery to monitor soil moisture, crop growth, irrigation events, and drought, leveraging the spectral sensitivity of these optical indices alongside all-weather radar (litreview Report A §3.1). A limitation is that cloud cover limits optical-data availability (litreview Report A §3.4).

## Role in this methodology

Sentinel 2 is the workhorse optical channel of the [[Earth Observation Layer]] and the origin of the index covariates used to diagnose crop condition and water status. Its pairing with radar [[Sentinel 1]] is the established backbone documented in [[Sentinel 1 and Sentinel 2 Integration]]; it is also the partner with which higher-resolution PlanetScope imagery is typically fused.

## Related

[[NDVI]] · [[NDWI]] · [[NDMI]] · [[Sentinel 1]] · [[Earth Observation Layer]] · [[Sentinel 1 and Sentinel 2 Integration]]
