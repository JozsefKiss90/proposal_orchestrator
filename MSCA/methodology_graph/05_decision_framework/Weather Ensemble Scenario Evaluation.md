---
id: METH-DEC-004
title: "Weather Ensemble Scenario Evaluation"
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
  - "methodology_idea.txt ('run the model forward under all the candidate decisions, over weather ensembles, and steer toward the one with the best expected outcome')"
  - "prompt.txt §6 ('runs each candidate decision under multiple possible weather futures. Then it compares expected outcomes')"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Counterfactual Irrigation Simulation]]"
downstream_nodes: []
related_nodes:
  - "[[Prognostic Branch]]"
  - "[[Weather and Climate Data Layer]]"
  - "[[Uncertainty Chain]]"
key_terms:
  - "[[Weather Ensemble]]"
  - "[[Uncertainty Propagation]]"
  - "[[Expected Utility]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Weather scenario evaluation"
tags:
  - methodology-graph
  - decision
---

# Weather Ensemble Scenario Evaluation

Running each candidate irrigation decision over **multiple plausible future weather paths** (a **[[Weather Ensemble]]**) and aggregating the results into an expected outcome per decision.

## What it is

A [[Weather Ensemble]] is a set of **multiple plausible future weather paths** rather than one deterministic forecast. In this methodology, every option from the **[[Counterfactual Irrigation Simulation]]** is run **under multiple possible weather futures**, and the simulator then **compares expected outcomes** across decisions (prompt.txt §6). The PI's narrative ties the steps together: *"run the model forward under all the candidate decisions, over weather ensembles, and steer toward the one with the best expected outcome at the end of the season"* (methodology_idea.txt).

## Role in this methodology

This node is how future weather uncertainty is brought honestly into the decision. Because no single forecast is trusted, each decision is scored as an **expectation over the ensemble** — the practical form of **[[Expected Utility]]** used in the [[Prognostic Branch]]. Averaging over many futures rather than betting on one is also a concrete instance of **[[Uncertainty Propagation]]**: the weather uncertainty is carried forward into the comparison instead of being assumed away, keeping faith with the project's "red thread" recorded in **[[Uncertainty Chain]]**.

The weather paths themselves are sourced and assembled by the **[[Weather and Climate Data Layer]]** (rainfall, temperature, evapotranspiration, radiation, wind — prompt.txt §3/§8). The per-decision expected outcomes produced here are what downstream profit scoring and recommendation logic act on.

## Source grounding

- "over weather ensembles… best expected outcome at the end of the season": `methodology_idea.txt`.
- "runs each candidate decision under multiple possible weather futures. Then it compares expected outcomes": `prompt.txt §6`.

## Links & relationships

Upstream: [[Counterfactual Irrigation Simulation]]. Related: [[Prognostic Branch]], [[Weather and Climate Data Layer]], [[Uncertainty Chain]]. Key terms: [[Weather Ensemble]], [[Uncertainty Propagation]], [[Expected Utility]]. Hub: [[Methodology Graph - Meta Node]].
