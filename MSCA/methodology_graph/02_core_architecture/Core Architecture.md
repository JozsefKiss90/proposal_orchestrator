---
id: METH-CORE-001
title: "Core Architecture"
node_type: architecture
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
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "prompt.txt §1 (core architecture; two scientific blocks)"
  - "methodology_idea.txt (two branches: diagnostic + prognostic; one uncertainty chain)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes: []
downstream_nodes:
  - "[[Diagnostic Branch]]"
  - "[[Prognostic Branch]]"
  - "[[Uncertainty Chain]]"
  - "[[Observation to Decision Pipeline]]"
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[AquaCrop Decision Interface]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Infrastructure Architecture]]"
  - "[[State of the Art - Multi Sensor Crop Water Stress Monitoring]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Multimodal Fusion]]"
  - "[[Latent Field State]]"
  - "[[Uncertainty Propagation]]"
  - "[[Counterfactual Simulation]]"
  - "[[Expected Profit]]"
  - "[[Crop Water Stress]]"
risks: []
open_questions:
  - "See [[Ten Research Questions]] (target field state RQ3; decision objective RQ6; route scope RQ2)"
validation_needs:
  - "End-to-end uncertainty calibration (RQ5)"
aliases:
  - "Methodology Core Architecture"
tags:
  - methodology-graph
  - core
---

# Core Architecture

The core architecture is the end-to-end backbone of the methodology: a pipeline that turns multiple uncertain observation streams into a probabilistic diagnosis of the crop/soil/water system, and then into an economically optimized irrigation decision, with uncertainty carried honestly from one end to the other.

## What it is

In one line, the proposal-friendly form of the method is:

> [!note] Pipeline (prompt.txt §1)
> Satellite + soil sensors + weather + field observations → probabilistic field-state diagnosis → uncertainty-aware AquaCrop calibration → counterfactual irrigation simulations → profit/risk-based recommendation.

The architecture decomposes the problem into **two scientific blocks** (prompt.txt §1; methodology_idea.txt frames them as the two "branches"):

| Block | Plain meaning | Scientific role |
|---|---|---|
| Diagnostic block | What is happening now in the crop/soil system? | Estimate water stress, soil moisture, crop condition, phenology — the [[Latent Field State]] |
| Prognostic block | What happens if we choose irrigation option A, B, C? | Run counterfactual futures and select the best decision |

These map to the two architecture children: the [[Diagnostic Branch]] ("what is the actual state of the field, the plant, the soil, the water?") and the [[Prognostic Branch]] ("given that state, what would happen under the different decisions, so that we can pick the best one"). They are joined by the [[Observation to Decision Pipeline]], which lays out the linear stage chain, and bound together by the [[Uncertainty Chain]].

## Role in this methodology

This node is the architectural hub that every other family of nodes hangs from. It uses [[Data Fusion]] and [[Multimodal Fusion]] to combine radar, optical, soil and weather signals into estimates of the [[Latent Field State]] (the diagnostic side), then drives [[Counterfactual Simulation]] of irrigation options whose outcomes are scored by [[Expected Profit]] (the prognostic side). The central diagnostic target throughout is [[Crop Water Stress]].

The diagnostic block can be realised by either of two interchangeable methodological routes that share the same downstream decision engine: the rigorous one-step [[Route A - Direct Probabilistic Fusion]], or the lighter [[Route B - Homogeneous Patch Proxy]]. As the source narrative puts it, *"from the diagnosed state onward the path is the same for both"* — both feed the [[AquaCrop Decision Interface]], which "stands for the plant" and is the interface through which decisions act (methodology_idea.txt).

## The red thread: uncertainty

The architecture's defining commitment is that the two blocks are *"tied together by one chain that carries its uncertainty from end to end, and keeping that uncertainty honest is … the heart of the whole thing"* (methodology_idea.txt). Every model output must report not only the state but how sure we are, and that uncertainty must travel into the decision via [[Uncertainty Propagation]]. This is detailed in the [[Uncertainty Chain]].

## Source grounding

- The pipeline string and the two-block decomposition are stated directly in `prompt.txt §1`.
- The "two branches tied by one uncertainty chain" framing and the shared downstream path are from `methodology_idea.txt`.
- The literature supports the *framing* of multi-sensor diagnosis; however, the integrated "fusion → probabilistic drought state → optimized irrigation" chain *"is not yet well established"* (prompt.txt §1) — see [[Probabilistic Fusion Novelty Claim]] and [[State of the Art - Multi Sensor Crop Water Stress Monitoring]].

*(Synthesis note: this node combines the PI narrative and the analyst synthesis into a single canonical architecture view; the combination is the synthesis, the individual claims are source-grounded.)*

## Links and relationships

Downstream: [[Diagnostic Branch]] · [[Prognostic Branch]] · [[Uncertainty Chain]] · [[Observation to Decision Pipeline]]. Related: [[Route A - Direct Probabilistic Fusion]] · [[Route B - Homogeneous Patch Proxy]] · [[AquaCrop Decision Interface]] · [[Probabilistic Fusion Novelty Claim]] · [[Infrastructure Architecture]] · [[State of the Art - Multi Sensor Crop Water Stress Monitoring]]. Up: [[Methodology Graph - Meta Node]].

## Open questions

The architecture leaves several scoping choices open (see [[Ten Research Questions]]): the exact target field state (RQ3), the decision objective (RQ6), and whether both routes are implemented or one is the main method with the other a fallback (RQ2).
