---
id: METH-TERM-022
title: "Evapotranspiration"
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
  - "prompt.txt §3 (weather inputs: evapotranspiration)"
  - "litreview Report A §3.3 (ETc estimation)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Weather and Climate Data Layer]]"
key_terms:
  - "[[Irrigation Water Requirement]]"
  - "[[Crop Water Stress]]"
  - "[[AquaCrop]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - ET
  - ETc
tags:
  - methodology-graph
  - terminology
---

# Evapotranspiration

The combined loss of water from a field through soil evaporation and plant transpiration.

## Definition / What it is

Evapotranspiration (ET) is the total water flux leaving the crop-soil system as the sum of evaporation from the soil surface and transpiration by the plant canopy. When scaled to a specific crop it is often written ETc. ET is one of the weather-related inputs the methodology lists alongside rainfall, temperature, radiation, and wind (prompt.txt §3). The literature review notes that combining satellite-derived indices with meteorological datasets and in-situ soil-moisture sensors improves estimates of ETc, irrigation water requirements, and root-zone moisture status (litreview Report A §3.3).

## Role in this methodology

ET quantifies crop water demand, so it sits at the heart of both diagnosis and decision. It directly determines the [[Irrigation Water Requirement]] (water demand net of natural supply) and is closely tied to [[Crop Water Stress]], which arises when supply cannot meet evaporative demand. ET-related inputs are carried by the [[Weather and Climate Data Layer]], and the crop-growth model [[AquaCrop]] uses water balance — including ET — to simulate yield response to water.

## Related

[[Irrigation Water Requirement]] · [[Crop Water Stress]] · [[Weather and Climate Data Layer]] · [[AquaCrop]]
