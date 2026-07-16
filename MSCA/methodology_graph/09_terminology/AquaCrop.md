---
id: METH-TERM-015
title: "AquaCrop"
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
  - "[[Source - Methodology Idea]]"
evidence_basis:
  - "prompt.txt §5 (FAO crop growth model; yield response to water)"
  - "methodology_idea.txt (stands for the plant; interface decisions act through)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[AquaCrop Decision Interface]]"
  - "[[AquaCrop Simulation Runtime]]"
  - "[[Uncertainty Aware AquaCrop Calibration]]"
key_terms:
  - "[[Evapotranspiration]]"
  - "[[Crop Water Stress]]"
  - "[[Irrigation Water Requirement]]"
aliases:
  - "FAO AquaCrop"
risks: []
open_questions: []
validation_needs: []
tags:
  - methodology-graph
  - terminology
---

# AquaCrop

The FAO crop-growth model that simulates yield response to water; especially suited to situations where water is the limiting factor.

## Definition / What it is

AquaCrop is described by FAO as a crop growth model that simulates yield response to water and is especially suited where water is a limiting factor (prompt.txt §5). In this methodology it is a "simple" process model that plays two roles at once: it stands for the plant, and it is the interface through which the decisions act (methodology_idea.txt).

## Role in this methodology

AquaCrop is the bridge from monitoring to decision-making (prompt.txt §5). It takes the diagnosed field state and asks counterfactual questions — what if we irrigate today, delay, apply less water, face high water prices, or meet dry/wet/hot weather — becoming the decision simulator. This is filed in [[AquaCrop Decision Interface]] and executed via the [[AquaCrop Simulation Runtime]]. Its parameters are fit through [[Uncertainty Aware AquaCrop Calibration]] so an honest range, not one overconfident set, is retained (methodology_idea.txt). It is strongest in irrigation, where the project begins; relevant variables include [[Evapotranspiration]], [[Crop Water Stress]], and [[Irrigation Water Requirement]].

## Related

[[AquaCrop Decision Interface]] · [[AquaCrop Simulation Runtime]] · [[Uncertainty Aware AquaCrop Calibration]] · [[Evapotranspiration]] · [[Crop Water Stress]] · [[Irrigation Water Requirement]]
