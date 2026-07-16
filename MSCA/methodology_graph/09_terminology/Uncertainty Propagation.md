---
id: METH-TERM-012
title: "Uncertainty Propagation"
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
  - "prompt.txt §3 (red thread)"
  - "methodology_idea.txt (one chain carrying uncertainty end-to-end)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Uncertainty Chain]]"
  - "[[Downscaling Critique]]"
  - "[[Decision Recommendation Logic]]"
  - "[[Weather Ensemble Scenario Evaluation]]"
key_terms:
  - "[[Posterior Distribution]]"
risks: []
open_questions: []
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Uncertainty Propagation

Carrying uncertainty from the input data through every model step all the way to the final decision — the project's "red thread."

## Definition / What it is

Uncertainty propagation means that uncertainty is not discarded at any stage: it is carried from the inputs, through each modelling step, into the final decision (prompt.txt §7). In this project it is *the* organising principle — "every model output should say not only what is the state but how sure are we, and that uncertainty must travel all the way into the irrigation decision" (prompt.txt §3; methodology_idea.txt: "one chain that carries its uncertainty from end to end").

## Role in this methodology

It is the substance of the [[Uncertainty Chain]] that links diagnosis to decision. The diagnostic step emits a [[Posterior Distribution]] of the field state; that uncertainty then flows into [[Weather Ensemble Scenario Evaluation]] and finally into [[Decision Recommendation Logic]], so recommendations reflect how confident the diagnosis was. It also motivates the [[Downscaling Critique]]: the two-step downscaling route inflates error multiplicatively and treats an estimated pixel as if measured, breaking honest propagation (methodology_idea.txt).

## Related

[[Uncertainty Chain]] · [[Posterior Distribution]] · [[Downscaling Critique]] · [[Decision Recommendation Logic]] · [[Weather Ensemble Scenario Evaluation]]
