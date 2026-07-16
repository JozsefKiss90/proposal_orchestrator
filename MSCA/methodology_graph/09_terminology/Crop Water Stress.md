---
id: METH-TERM-020
title: "Crop Water Stress"
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
  - "prompt.txt §1, §3 (plant water stress as diagnostic target / hidden state)"
  - "litreview Report A title and Report B (drought stress monitoring in row crops)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Diagnostic Branch]]"
  - "[[Latent Field State]]"
key_terms:
  - "[[Root Zone Soil Moisture]]"
  - "[[Evapotranspiration]]"
  - "[[NDWI]]"
  - "[[NDMI]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Drought stress"
  - "Plant water stress"
tags:
  - methodology-graph
  - terminology
---

# Crop Water Stress

The plant condition that arises when water supply is insufficient for water demand — the project's central diagnostic target.

## Definition / What it is

Crop water stress (also drought stress, plant water stress) is the condition where the water available to a crop is insufficient to meet its demand. It is a core quantity in the project's hidden field state — the diagnostic block estimates water stress, soil moisture, crop condition, and phenology (prompt.txt §1, §3) — and is the monitoring target named throughout the literature review (drought stress monitoring in row crops; litreview Report A title, Report B).

## Role in this methodology

Crop water stress is a primary output of the [[Diagnostic Branch]] and a key component of the [[Latent Field State]]. It is driven by [[Root Zone Soil Moisture]] and [[Evapotranspiration]] — stress emerges when available root-zone water cannot keep up with evaporative demand. Optical indices from Sentinel-2, especially [[NDWI]] and [[NDMI]], are signals used to detect it. Diagnosing crop water stress with honest uncertainty is what the downstream irrigation decision acts on. The precise definition of the target field state (stress alone, or also yield risk and irrigation priority) is an open project decision (RQ3).

## Related

[[Root Zone Soil Moisture]] · [[Evapotranspiration]] · [[NDWI]] · [[NDMI]] · [[Diagnostic Branch]] · [[Latent Field State]]
