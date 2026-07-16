---
id: METH-TERM-007
title: "Bayesian Hierarchical Model"
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
  - "prompt.txt §3 (Route 1 models — Bayesian hierarchical model)"
  - "prompt.txt §7 (terminology)"
  - "methodology_idea.txt (Bayesian hierarchical model as one probabilistic ML option)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Probabilistic Modelling Runtime]]"
  - "[[Uncertainty Chain]]"
key_terms:
  - "[[Gaussian Process]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Posterior Distribution]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "BHM"
tags:
  - methodology-graph
  - terminology
---

# Bayesian Hierarchical Model

**Bayesian hierarchical model (BHM)** is a statistical model that estimates both field-level effects and general crop/soil/weather relationships while explicitly producing uncertainty ranges ([[Source - Methodology Synthesis Prompt]] §3).

## Definition / What it is
A BHM organises parameters in levels ("hierarchies"): local effects specific to a field nest within broader population-level relationships shared across fields. Because it is Bayesian, every quantity is estimated as a [[Posterior Distribution]] rather than a single point, so uncertainty is built in by design.

## Role in this methodology
The BHM is one of the candidate engines for [[Route A - Direct Probabilistic Fusion]], alongside the [[Gaussian Process]] and other [[Probabilistic Machine Learning]] methods ([[Source - Methodology Idea]]; [[Source - Methodology Synthesis Prompt]] §3). It takes the fused satellite, sensor, soil and weather covariates and goes straight to the field state *with its uncertainty*, supporting the project's red thread (the [[Uncertainty Chain]]). It runs on the [[Probabilistic Modelling Runtime]]. The PI also applies uncertainty-aware ideas downstream when calibrating AquaCrop, keeping an honest parameter range rather than one overconfident set.

## Related
[[Gaussian Process]] · [[Probabilistic Machine Learning]] · [[Posterior Distribution]] · [[Route A - Direct Probabilistic Fusion]] · [[Probabilistic Modelling Runtime]] · [[Uncertainty Chain]]
