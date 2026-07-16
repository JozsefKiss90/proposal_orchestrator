---
id: METH-TERM-010
title: "Latent Field State"
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
  - "prompt.txt §7 (terminology — latent state)"
  - "prompt.txt §3 (estimates the hidden state of the field)"
  - "methodology_idea.txt (diagnostic: actual state of field/plant/soil/water; goes straight to field state)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Diagnostic Branch]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
key_terms:
  - "[[Posterior Distribution]]"
  - "[[Crop Water Stress]]"
  - "[[Root Zone Soil Moisture]]"
risks: []
open_questions:
  - "RQ3 — exactly what is the target field state (soil moisture, crop water stress, yield risk, irrigation priority, or all)? (decision needed)"
validation_needs: []
aliases:
  - "Latent state"
  - "Hidden state"
  - "Field state"
tags:
  - methodology-graph
  - terminology
---

# Latent Field State

**Latent field state** is the real but not directly observed condition of the crop/soil system — the diagnostic target the model infers ([[Source - Methodology Synthesis Prompt]] §7).

## Definition / What it is
"Latent" (or hidden) means it cannot be measured directly from any single sensor; it must be inferred from the available signals. In this project the hidden state spans [[Root Zone Soil Moisture]], plant [[Crop Water Stress]], canopy development, biomass and expected yield ([[Source - Methodology Synthesis Prompt]] §3).

## Role in this methodology
Estimating the latent field state is the whole job of the [[Diagnostic Branch]] — "what is happening now in the crop/soil system" ([[Source - Methodology Idea]]). [[Route A - Direct Probabilistic Fusion]] fuses all covariates and goes *straight to the field state with its uncertainty*, representing it as a [[Posterior Distribution]] rather than a single number. That posterior is what feeds the prognostic side and keeps the uncertainty chain honest into the decision.

> [!note]
> The precise definition of the target field state — soil moisture, crop water stress, yield risk, irrigation priority, or all of these — is still a decision for the team (RQ3).

## Related
[[Posterior Distribution]] · [[Diagnostic Branch]] · [[Crop Water Stress]] · [[Root Zone Soil Moisture]] · [[Route A - Direct Probabilistic Fusion]]
