---
id: METH-TERM-005
title: "Downscaling"
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
  - "prompt.txt §7 (terminology)"
  - "prompt.txt §2 (sub-pixel problem & downscaling critique)"
  - "methodology_idea.txt (downscaling: statistical layer turns covariates into a fine pixel)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Sub Pixel Problem]]"
  - "[[Downscaling Critique]]"
key_terms:
  - "[[Cokriging]]"
  - "[[Covariate]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Spatial downscaling"
tags:
  - methodology-graph
  - terminology
---

# Downscaling

**Downscaling** is estimating finer-resolution information from coarse-resolution data ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
Downscaling turns a coarse satellite observation into a finer-resolution map using statistical or machine-learning models. The PI's narrative describes it as a statistical layer — for example [[Cokriging]] or deep learning — that first turns [[Covariate]]s into a fine pixel, after which a second model turns that pixel into the prediction ([[Source - Methodology Idea]]).

## Role in this methodology
Downscaling is the "obvious, almost too obvious" answer to the [[Sub Pixel Problem]], and the project deliberately argues *against* relying on it as a two-step chain. The [[Downscaling Critique]] node sets out why: `covariates → estimated fine pixel → prediction` propagates error multiplicatively (the second step inflates what the first carries) and conditions on an estimated pixel as if it had been measured ([[Source - Methodology Synthesis Prompt]] §2; [[Source - Methodology Idea]]). The proposed alternative skips the pixel entirely, using `covariates + uncertainty → prediction` directly.

> [!note]
> The concern is not [[Cokriging]] itself — it does carry its own uncertainty — but the two-step structure of downscaling.

## Related
[[Cokriging]] · [[Sub Pixel Problem]] · [[Downscaling Critique]] · [[Covariate]]
