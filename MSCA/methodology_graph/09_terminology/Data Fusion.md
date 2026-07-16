---
id: METH-TERM-001
title: "Data Fusion"
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
  - "prompt.txt §1 (core architecture)"
  - "litreview Report B (multimodal data fusion is mature)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Core Architecture]]"
key_terms:
  - "[[Multimodal Fusion]]"
  - "[[Covariate]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Data integration"
tags:
  - methodology-graph
  - terminology
---

# Data Fusion

**Data fusion** is the practice of combining different data sources into one model rather than analysing each in isolation ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
In plain terms, data fusion brings several distinct data streams together so that a single model can exploit their joint information. In this project the streams include satellite imagery, in-situ soil sensors, weather records and field observations, all merged into one estimate of the crop/soil/water condition.

## Role in this methodology
Data fusion is the entry point of the [[Core Architecture]]: `satellite + soil sensors + weather + field observations → probabilistic field-state diagnosis`. The "hardcore" [[Route A - Direct Probabilistic Fusion]] takes this furthest by feeding every source — including satellite — directly into one probabilistic model as [[Covariate]]s, going straight to the field state with its uncertainty in a single step. The closely related notion of [[Multimodal Fusion]] sharpens the idea to combining different *types* of signal.

The literature confirms that fusing multiple sources for crop status is well established; per [[Source - Literature Review]] (Report B), "multimodal data fusion is mature", while embedding it in an explicit probabilistic, decision-optimisation framework is what remains underdeveloped.

## Related
[[Multimodal Fusion]] · [[Covariate]] · [[Route A - Direct Probabilistic Fusion]] · [[Core Architecture]]
