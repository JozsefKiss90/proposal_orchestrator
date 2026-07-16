---
id: METH-TERM-019
title: "Root Zone Soil Moisture"
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
  - "prompt.txt §3 (hidden state: root-zone soil moisture)"
  - "litreview Report A §3.3 (ERA5-Land + in-situ soil moisture improve root-zone moisture)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Latent Field State]]"
  - "[[Diagnostic Branch]]"
  - "[[Ground Sensing Layer]]"
key_terms:
  - "[[Crop Water Stress]]"
  - "[[Evapotranspiration]]"
  - "[[SAR]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "RZSM"
tags:
  - methodology-graph
  - terminology
---

# Root Zone Soil Moisture

The water available in the crop root zone — a key, not-directly-observed diagnostic state variable.

## Definition / What it is

Root zone soil moisture (RZSM) is the water available in the layer of soil occupied by crop roots. It is one of the hidden-state quantities the diagnostic model estimates from fused observations (prompt.txt §3) and is part of the broader [[Latent Field State]] the project aims to recover.

## Role in this methodology

RZSM is a central target of the [[Diagnostic Branch]] — "what is happening now" includes soil moisture (prompt.txt §1, §3). It is informed by in-situ probes in the [[Ground Sensing Layer]] and by [[SAR]] (Sentinel-1), which is sensitive to surface structure and moisture; the literature shows that combining ERA5-Land with in-situ soil moisture improves root-zone moisture estimates, with hybrid physical–ML models outperforming physical-only baselines (litreview Report A §3.3). Together with [[Evapotranspiration]], RZSM underlies [[Crop Water Stress]]: when root-zone water cannot meet crop demand, stress develops. Exactly which field-state variables are the primary target is an open project decision (RQ3).

## Related

[[Crop Water Stress]] · [[Evapotranspiration]] · [[Latent Field State]] · [[Diagnostic Branch]] · [[Ground Sensing Layer]] · [[SAR]]
