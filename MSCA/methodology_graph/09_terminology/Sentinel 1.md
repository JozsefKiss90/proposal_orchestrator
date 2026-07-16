---
id: METH-TERM-028
title: "Sentinel 1"
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
  - "[[SAR]]"
  - "[[Sentinel 2]]"
  - "[[Earth Observation Layer]]"
  - "[[Sentinel 1 and Sentinel 2 Integration]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - S1
  - Sentinel-1
tags:
  - methodology-graph
  - terminology
---

# Sentinel 1

The Copernicus radar satellite — all-weather imaging via Synthetic Aperture Radar.

## Definition / What it is

Sentinel 1 is the radar satellite in the Copernicus programme, carrying [[SAR]] (Synthetic Aperture Radar). Because it is radar-based it works through cloud cover and is sensitive to surface structure and moisture (prompt.txt §3). The literature review reports that most studies integrate two or three data types, commonly Sentinel-1 SAR with [[Sentinel 2]] optical imagery, to monitor soil moisture, crop growth, irrigation events, and drought; the Discussion calls dual-sensor (Sentinel-1 + Sentinel-2) approaches "now standard practice" (litreview Report A §3.1, §4).

## Role in this methodology

Sentinel 1 supplies the weather-independent radar signal within the [[Earth Observation Layer]]. Its pairing with optical Sentinel-2 is the established foundation documented in [[Sentinel 1 and Sentinel 2 Integration]] (the strongest-evidence claim in the review). Its all-weather capability complements cloud-limited optical indices in the fused diagnosis.

## Related

[[SAR]] · [[Sentinel 2]] · [[Earth Observation Layer]] · [[Sentinel 1 and Sentinel 2 Integration]]
