---
id: METH-TERM-003
title: "Ground Truth"
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
  - "methodology_idea.txt (ground truth + signals are the easy part; validation is where it lives or dies)"
  - "litreview Report A (few large-scale validation efforts with dense ground-truth networks)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Validation and Field Trial Layer]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Control Stand Variant]]"
key_terms:
  - "[[Covariate]]"
risks: []
open_questions:
  - "RQ4 — what ground-truth measurements will be collected? (open)"
validation_needs:
  - "Define the ground-truth dataset and collection protocol."
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Ground Truth

**Ground truth** is the set of real field measurements used to train or validate the model ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
Ground truth is the trusted reference against which model estimates are checked — direct, in-field observations of the quantities the system tries to infer (soil moisture, crop water stress, biomass, yield, etc.). It is distinct from the satellite and sensor *signals* the model consumes: ground truth is the answer key, not an input.

## Role in this methodology
Ground truth anchors the [[Validation and Field Trial Layer]], where field trials, sensor comparison and model-accuracy checks confirm whether the probabilistic estimates are trustworthy. The PI's narrative notes that gathering the ground truth and signals is "the easy part"; the project "lives or dies" on the fusion, modelling and *validation* that turn them into a decision ([[Source - Methodology Idea]]). For [[Route B - Homogeneous Patch Proxy]] and its [[Control Stand Variant]], ground truth is what lets the team *measure* — rather than assume — that the proxy patch covaries with the target crop.

> [!note]
> The state of the art ([[Source - Literature Review]], Report A) flags that few large-scale efforts validate multi-sensor frameworks against dense ground-truth networks — a gap this project must address. Exactly which measurements to collect is still open (RQ4).

## Related
[[Validation and Field Trial Layer]] · [[Route B - Homogeneous Patch Proxy]] · [[Control Stand Variant]] · [[Covariate]]
