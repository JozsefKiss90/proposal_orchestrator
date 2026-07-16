---
id: METH-TERM-002
title: "Multimodal Fusion"
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
  - "prompt.txt §7 (terminology)"
  - "prompt.txt §3 (Route 1 inputs)"
  - "litreview Report A §3.1 (S1 SAR + S2 optical integration)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[SAR]]"
  - "[[NDVI]]"
  - "[[Sentinel 1]]"
  - "[[Sentinel 2]]"
  - "[[PlanetScope]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Multi-modal fusion"
  - "Multi-source fusion"
tags:
  - methodology-graph
  - terminology
---

# Multimodal Fusion

**Multimodal fusion** is the combining of different *types* of signal — for example radar, optical imagery, in-situ sensors and weather data — into one model ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
It is a more specific form of [[Data Fusion]]: where data fusion merely means "more than one source", multimodal fusion stresses that the sources are of fundamentally different *modalities* (active radar vs. passive optical vs. ground-point sensors vs. meteorological time series). Each modality carries complementary information, so combining them can reveal what no single modality sees cleanly.

## Role in this methodology
Multimodal fusion underpins [[Route A - Direct Probabilistic Fusion]], whose inputs span [[SAR]] radar from [[Sentinel 1]], optical indices such as [[NDVI]] from [[Sentinel 2]], higher-resolution [[PlanetScope]] imagery, weather variables and soil sensors — all fed together to estimate the field state ([[Source - Methodology Synthesis Prompt]] §3). The state-of-the-art confirms the value of mixing modalities: per [[Source - Literature Review]] (Report A §3.1), pairing all-weather [[Sentinel 1]] SAR with [[Sentinel 2]] optical indices improves drought and crop-status detection over single-sensor approaches.

## Related
[[Data Fusion]] · [[SAR]] · [[NDVI]] · [[Sentinel 1]] · [[Sentinel 2]] · [[PlanetScope]] · [[Route A - Direct Probabilistic Fusion]]
