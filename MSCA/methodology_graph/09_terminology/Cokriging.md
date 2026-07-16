---
id: METH-TERM-006
title: "Cokriging"
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
  - "methodology_idea.txt (cokriging carries its own uncertainty; the issue is the two steps)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Downscaling Critique]]"
key_terms:
  - "[[Downscaling]]"
  - "[[Covariate]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Co-kriging"
tags:
  - methodology-graph
  - terminology
---

# Cokriging

**Cokriging** is a geostatistical interpolation method that uses correlated auxiliary variables to predict a target field, and it carries its own uncertainty ([[Source - Methodology Synthesis Prompt]] §7; [[Source - Methodology Idea]]).

## Definition / What it is
Cokriging extends ordinary kriging by exploiting one or more correlated [[Covariate]]s ("auxiliary variables") to improve interpolation of a primary variable. Like other geostatistical methods it returns not just an estimate but an associated uncertainty.

## Role in this methodology
Cokriging is named as one of the statistical layers used in classical [[Downscaling]] — turning covariates into a fine pixel before a second model makes the prediction. Importantly, the PI's narrative is explicit that cokriging itself is *not* the problem: it "does carry its own uncertainty, so that is not the issue" ([[Source - Methodology Idea]]). The objection set out in the [[Downscaling Critique]] is to the **two-step** structure (covariates → estimated pixel → prediction), which inflates error multiplicatively and treats an estimated pixel as if it had been measured — not to cokriging as a technique.

> [!note]
> Citing cokriging here is faithful to its role in the sources as an *example* of a downscaling layer, not an endorsement of the two-step pipeline.

## Related
[[Downscaling]] · [[Covariate]] · [[Downscaling Critique]]
