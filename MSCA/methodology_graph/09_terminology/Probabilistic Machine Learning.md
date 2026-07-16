---
id: METH-TERM-009
title: "Probabilistic Machine Learning"
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
  - "prompt.txt §3 (Route 1 — probabilistic ML returns distributions/intervals)"
  - "prompt.txt §7 (terminology)"
  - "methodology_idea.txt (probabilistic machine learning model: BHM or GP)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Probabilistic Fusion Novelty Claim]]"
key_terms:
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Posterior Distribution]]"
  - "[[Uncertainty Propagation]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Probabilistic ML"
tags:
  - methodology-graph
  - terminology
---

# Probabilistic Machine Learning

**Probabilistic machine learning** is any ML approach that returns distributions or confidence intervals rather than just point predictions ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
Where a conventional model outputs a single number, probabilistic ML outputs a full predictive distribution — a best estimate together with a quantified range. This is the property the project needs so that every model output can say *how sure* it is.

## Role in this methodology
Probabilistic ML is the model class behind [[Route A - Direct Probabilistic Fusion]]: the PI's narrative names the [[Bayesian Hierarchical Model]] and the [[Gaussian Process]] as specific examples ([[Source - Methodology Idea]]; [[Source - Methodology Synthesis Prompt]] §3). Each returns the field state as a [[Posterior Distribution]], which is what makes honest [[Uncertainty Propagation]] possible all the way to the irrigation decision.

It is also where the [[Probabilistic Fusion Novelty Claim]] sits: per [[Source - Literature Review]] (Report B), multimodal fusion is mature but coupling *rich* fusion directly with *explicit probabilistic outputs* for row-crop drought stress and irrigation remains rare — the defendable edge.

## Related
[[Bayesian Hierarchical Model]] · [[Gaussian Process]] · [[Posterior Distribution]] · [[Uncertainty Propagation]] · [[Probabilistic Fusion Novelty Claim]]
