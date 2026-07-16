---
id: METH-TERM-021
title: "Irrigation Water Requirement"
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
  - "litreview Report A §3.3 (ETc/IWR/root-zone moisture)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Meteorological and Soil Sensor Integration]]"
  - "[[Profit Based Objective Function]]"
key_terms:
  - "[[Evapotranspiration]]"
  - "[[AquaCrop]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - IWR
tags:
  - methodology-graph
  - terminology
---

# Irrigation Water Requirement

The depth of water that must be supplied by irrigation to meet crop demand, net of what rainfall and stored soil water already provide.

## Definition / What it is

Irrigation Water Requirement (IWR) is the additional water a crop needs from irrigation once natural supply (rainfall, soil-stored water) is subtracted from total crop water demand. Crop demand is driven largely by crop [[Evapotranspiration]] (ETc), so IWR is tightly coupled to ET estimates. The literature review reports that integrating satellite-derived indices with meteorological datasets (e.g. ERA5-Land) and in-situ soil-moisture sensors improves estimates of ETc, IWR, and root-zone moisture status (litreview Report A §3.3).

## Role in this methodology

IWR is part of the quantitative bridge between diagnosis and decision. Better ETc/IWR estimation is one of the benefits of [[Meteorological and Soil Sensor Integration]], which combines satellite, weather, and soil signals. On the decision side, the water actually applied carries a cost, so IWR feeds into the [[Profit Based Objective Function]] (expected crop value minus water and input costs). The crop-growth model [[AquaCrop]] simulates yield response to water and is the interface through which candidate irrigation amounts are evaluated.

## Related

[[Evapotranspiration]] · [[AquaCrop]] · [[Meteorological and Soil Sensor Integration]] · [[Profit Based Objective Function]]
