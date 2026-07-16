---
id: METH-CORE-004
title: "Uncertainty Chain"
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
  - "[[Source - Literature Review]]"
evidence_basis:
  - "methodology_idea.txt (one chain carries uncertainty end-to-end; keeping it honest is the heart of the whole thing)"
  - "prompt.txt §3 (red thread: how sure are we?; uncertainty must travel into the decision)"
  - "prompt.txt §5 (uncertainty-aware AquaCrop calibration; retain parameter uncertainty)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Core Architecture]]"
  - "[[Diagnostic Branch]]"
  - "[[Prognostic Branch]]"
  - "[[Uncertainty Aware AquaCrop Calibration]]"
  - "[[Downscaling Critique]]"
  - "[[Probabilistic Fusion Novelty Claim]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Uncertainty Propagation]]"
  - "[[Posterior Distribution]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Decision Regret]]"
risks: []
open_questions:
  - "How will uncertainty be evaluated — e.g. do 90% prediction intervals contain the truth ~90% of the time? (RQ5)"
validation_needs:
  - "Uncertainty calibration / prediction-interval coverage (RQ5)"
aliases:
  - "Red Thread"
  - "End-to-End Uncertainty Chain"
tags:
  - methodology-graph
  - core
---

# Uncertainty Chain

The uncertainty chain is the "red thread" of the methodology: a single thread of honest uncertainty that runs from the raw observations, through diagnosis and model calibration, all the way into the irrigation decision — so that every output reports not just *what* the state is but *how sure* we are.

## What it is

The PI narrative names this the defining feature of the design: the diagnostic and prognostic branches are *"tied together by one chain that carries its uncertainty from end to end, and keeping that uncertainty honest is, for me, the heart of the whole thing"* (methodology_idea.txt). The analyst synthesis states the same as the red thread: *"every model output should say not only 'what is the state?' but also 'how sure are we?', and that uncertainty must travel all the way into the irrigation decision"* (prompt.txt §3 / intro).

The mechanism behind the chain is [[Uncertainty Propagation]]: carrying uncertainty from the inputs through every model step to the final decision, rather than discarding it at any stage.

## Role in this methodology

The chain is not a separate processing stage but a constraint that binds the whole [[Core Architecture]] together. It threads through:

1. **Diagnosis** — the [[Diagnostic Branch]] outputs a [[Posterior Distribution]] over the [[Latent Field State]] instead of a point estimate, using [[Probabilistic Machine Learning]] methods such as a [[Bayesian Hierarchical Model]] or a [[Gaussian Process]] that return distributions and uncertainty surfaces (prompt.txt §3).
2. **Calibration** — the [[Uncertainty Aware AquaCrop Calibration]] *"keeps an honest range rather than one overconfident parameter set"* (methodology_idea.txt), following the PI's prior method (doi:10.1016/j.envsoft.2022.105556; described by the analyst as a conditional interval reduction method that retains parameter uncertainty — prompt.txt §5).
3. **Decision** — the [[Prognostic Branch]] folds weather and model uncertainty into the comparison of options, where it ultimately informs [[Decision Regret]] and risk-aware recommendation.

## Why one step, not two

A key argument for the chain's integrity is the [[Downscaling Critique]]. The "obvious" two-step downscaling approach (covariates → estimated fine pixel → prediction) *"propagates the error multiplicatively"* and *"conditions on an estimated pixel as if it had been measured"* (methodology_idea.txt). The methodology instead uses the covariates **and their uncertainty directly** for the prediction in one step, so the chain stays honest and does not pretend an estimated quantity is an observed fact.

## Why it matters for novelty

Per Report B and the analyst synthesis, *"uncertainty propagation from fused observations into irrigation optimization is still rare"* — making a disciplined, end-to-end uncertainty chain a core part of the defendable [[Probabilistic Fusion Novelty Claim]] (litreview Report B; prompt.txt §9).

## Source grounding

- "One chain carries uncertainty end-to-end / heart of the whole thing": `methodology_idea.txt`.
- "How sure are we?" red thread into the decision: `prompt.txt` intro / §3.
- Probabilistic models returning distributions; uncertainty-aware calibration retaining a range: `prompt.txt §3`, `§5`; `methodology_idea.txt`; doi:10.1016/j.envsoft.2022.105556 (PI-stated).
- Uncertainty propagation into optimization still rare: `litreview Report B`.

## Links and relationships

Related: [[Core Architecture]] · [[Diagnostic Branch]] · [[Prognostic Branch]] · [[Uncertainty Aware AquaCrop Calibration]] · [[Downscaling Critique]] · [[Probabilistic Fusion Novelty Claim]]. Hub: [[Methodology Graph - Meta Node]].

## Open questions

How the chain's uncertainty will actually be *evaluated* is open: a concrete proposal is to check that 90% prediction intervals contain the true value about 90% of the time (RQ5, [[Ten Research Questions]]). This calibration test is a key validation need.
