---
id: METH-TERM-008
title: "Gaussian Process"
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
  - "prompt.txt §3 (Route 1 models — Gaussian process)"
  - "prompt.txt §7 (terminology)"
  - "methodology_idea.txt (Gaussian process as one probabilistic ML option)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
key_terms:
  - "[[Bayesian Hierarchical Model]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Posterior Distribution]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "GP"
tags:
  - methodology-graph
  - terminology
---

# Gaussian Process

**Gaussian process (GP)** is a probabilistic model especially useful for spatial or spatio-temporal prediction; it estimates both a value and an uncertainty surface ([[Source - Methodology Synthesis Prompt]] §3).

## Definition / What it is
A GP treats the unknown field as a distribution over functions, so any prediction comes paired with a calibrated uncertainty. Its natural handling of spatial and spatio-temporal correlation makes it well suited to mapping a quantity that varies smoothly across a field and over the season.

## Role in this methodology
The GP is one of the candidate engines for [[Route A - Direct Probabilistic Fusion]], named alongside the [[Bayesian Hierarchical Model]] as an example of [[Probabilistic Machine Learning]] ([[Source - Methodology Idea]]; [[Source - Methodology Synthesis Prompt]] §3). It fuses satellite, soil, weather and field covariates and returns the field state as a [[Posterior Distribution]] — a value plus an uncertainty surface — which keeps uncertainty honest from the very first model in the chain. Because it yields an explicit uncertainty surface, it directly serves the project's requirement that every output say not only *what* the state is but *how sure* we are.

## Related
[[Bayesian Hierarchical Model]] · [[Probabilistic Machine Learning]] · [[Posterior Distribution]] · [[Route A - Direct Probabilistic Fusion]]
