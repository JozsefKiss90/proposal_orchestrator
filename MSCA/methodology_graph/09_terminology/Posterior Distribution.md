---
id: METH-TERM-011
title: "Posterior Distribution"
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
  - "prompt.txt §7"
  - "methodology_idea.txt (uncertainty-aware calibration; honest range)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Latent Field State]]"
  - "[[Uncertainty Aware AquaCrop Calibration]]"
key_terms:
  - "[[Bayesian Hierarchical Model]]"
  - "[[Uncertainty Propagation]]"
  - "[[Latent Field State]]"
risks: []
open_questions: []
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Posterior Distribution

The model's updated uncertainty range after seeing the data — what the model believes about an unknown quantity once observations have been taken into account.

## Definition / What it is

A posterior distribution expresses, as a full range with probabilities rather than a single number, the model's belief about a hidden quantity after the data have been observed (prompt.txt §7). It is the natural output of probabilistic methods such as a [[Bayesian Hierarchical Model]] or a [[Gaussian Process]], which return distributions rather than point estimates.

## Role in this methodology

The posterior is how this project keeps uncertainty *honest*. The diagnostic step estimates the [[Latent Field State]] (root-zone moisture, crop water stress, biomass) not as a fixed value but as a posterior, so each output carries "how sure are we?" alongside "what is the state?" (prompt.txt §1, §3). That posterior is then the starting point for [[Uncertainty Propagation]] downstream into the decision. The PI's [[Uncertainty Aware AquaCrop Calibration]] follows the same logic: keep an honest parameter range rather than collapsing to one overconfident set (methodology_idea.txt).

## Related

[[Bayesian Hierarchical Model]] · [[Uncertainty Propagation]] · [[Latent Field State]] · [[Uncertainty Aware AquaCrop Calibration]]
