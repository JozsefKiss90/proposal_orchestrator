---
id: METH-DEC-002
title: "Uncertainty Aware AquaCrop Calibration"
node_type: decision_method
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
  - "methodology_idea.txt ('uncertainty-aware' calibration 'following a method I developed', doi: 10.1016/j.envsoft.2022.105556; 'honest range rather than one overconfident parameter set')"
  - "prompt.txt §5 ('Conditional interval reduction method' for optimizing process-based models while retaining parameter uncertainty — analyst's identification of the DOI)"
  - "doi:10.1016/j.envsoft.2022.105556 (Environmental Modelling & Software, 2022)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[AquaCrop Decision Interface]]"
downstream_nodes: []
related_nodes:
  - "[[Uncertainty Chain]]"
  - "[[Probabilistic Modelling Runtime]]"
  - "[[Model Complexity Risks]]"
  - "[[PI Role]]"
key_terms:
  - "[[Posterior Distribution]]"
  - "[[Uncertainty Propagation]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[AquaCrop]]"
risks: []
open_questions:
  - "RQ5: How will uncertainty be evaluated (e.g. do 90% prediction intervals contain the truth ~90% of the time)?"
validation_needs:
  - "Verify retained parameter uncertainty is calibrated (coverage) once project ground truth exists"
aliases:
  - "Conditional interval reduction method"
tags:
  - methodology-graph
  - decision
---

# Uncertainty Aware AquaCrop Calibration

Calibrating the **[[AquaCrop]]** model so that it keeps an **honest range of parameters** rather than collapsing to one overconfident set — applying a method the PI developed (doi: 10.1016/j.envsoft.2022.105556).

## What it is

When the [[AquaCrop Decision Interface]] is fitted to a field, calibration is **uncertainty-aware**: it deliberately **retains parameter uncertainty** instead of choosing a single "best" parameter vector. In the PI's words, the goal is *"to keep an honest range rather than one overconfident parameter set"* (methodology_idea.txt). This makes the model's [[Posterior Distribution]] over parameters part of the chain, so that the uncertainty already carried by the diagnosed field state is not silently discarded when the process model takes over.

The PI states this follows **a method I developed a few years ago, doi: 10.1016/j.envsoft.2022.105556** (Environmental Modelling & Software, 2022) — see [[PI Role]].

## Role in this methodology

This node is the point where the methodology's "red thread" — see **[[Uncertainty Chain]]** — passes *through* the process model rather than around it. The calibrated, uncertainty-bearing [[AquaCrop]] then drives the prognostic counterfactual runs; carrying the retained parameter spread forward is exactly what **[[Uncertainty Propagation]]** demands. Computationally this is supported by the **[[Probabilistic Modelling Runtime]]**, and the additional modelling and compute burden it implies is logged under **[[Model Complexity Risks]]** (overconfidence is itself a named risk there).

The link to **[[Probabilistic Machine Learning]]** is conceptual: like probabilistic ML, uncertainty-aware calibration returns ranges/distributions rather than point values, so the AquaCrop layer speaks the same probabilistic language as the diagnostic fusion model.

## On the method's title

> [!note] Analyst inference vs. source-given fact
> The **DOI itself is source-given** (the PI states it directly in methodology_idea.txt). The descriptive title *"Conditional interval reduction method"* — a way to calibrate process-based models while retaining parameter uncertainty — is the **analyst's identification** of that DOI (prompt.txt §5), labelled here as *(inference on the method's title)*. The DOI is the authoritative reference; treat the descriptive name as a working label until confirmed against the paper.

## Open question

> [!warning] Open — uncertainty evaluation protocol
> How retained uncertainty will actually be *evaluated* (e.g. whether 90% prediction intervals contain the truth about 90% of the time) is **RQ5** in the [[Ten Research Questions]] and is not yet decided. Calibrating uncertainty is one thing; verifying it is calibrated requires a validation protocol that still has to be specified.

## Source grounding

- "uncertainty-aware" calibration, the explicit DOI, and "honest range rather than one overconfident parameter set": `methodology_idea.txt`.
- The "Conditional interval reduction method" description and "retaining parameter uncertainty": `prompt.txt §5` (analyst's reading of the DOI).
- Reference: `doi:10.1016/j.envsoft.2022.105556` (Environmental Modelling & Software, 2022).

## Links & relationships

Upstream: [[AquaCrop Decision Interface]]. Related: [[Uncertainty Chain]], [[Probabilistic Modelling Runtime]], [[Model Complexity Risks]], [[PI Role]]. Key terms: [[Posterior Distribution]], [[Uncertainty Propagation]], [[Probabilistic Machine Learning]], [[AquaCrop]]. Hub: [[Methodology Graph - Meta Node]].
