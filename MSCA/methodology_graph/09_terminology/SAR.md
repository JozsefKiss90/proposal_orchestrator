---
id: METH-TERM-026
title: "SAR"
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
  - "prompt.txt §3 (Sentinel-1 radar: works through cloud, sensitive to surface structure/moisture)"
  - "litreview Report A §3.1 (SAR all-weather + optical), §3.4 (dense vegetation reduces SAR retrieval)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes: []
key_terms:
  - "[[Sentinel 1]]"
  - "[[Root Zone Soil Moisture]]"
  - "[[Multimodal Fusion]]"
  - "[[Earth Observation Layer]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - Synthetic Aperture Radar
tags:
  - methodology-graph
  - terminology
---

# SAR

Synthetic Aperture Radar — the all-weather radar imaging carried by Sentinel-1.

## Definition / What it is

SAR (Synthetic Aperture Radar) is active microwave imaging that works through cloud cover and is sensitive to surface structure and moisture (prompt.txt §3). It is the radar modality provided by [[Sentinel 1]]. The literature review notes that studies leverage the all-weather capability of SAR, combined with the spectral sensitivity of optical indices, to improve detection of soil moisture, crop growth, and drought (litreview Report A §3.1). A persistent limitation is that dense vegetation/canopy cover reduces SAR retrieval accuracy (litreview Report A §3.4; Claims & Evidence table — Moderate).

## Role in this methodology

SAR is the weather-independent backbone of the [[Earth Observation Layer]]. Because it penetrates cloud, it complements optical indices and is a core channel in [[Multimodal Fusion]] of radar, optical, sensor, and weather data. Its moisture sensitivity makes it directly relevant to estimating [[Root Zone Soil Moisture]], a key diagnostic state variable, while its dense-vegetation limitation is a known retrieval risk to manage.

## Related

[[Sentinel 1]] · [[Root Zone Soil Moisture]] · [[Multimodal Fusion]] · [[Earth Observation Layer]]
