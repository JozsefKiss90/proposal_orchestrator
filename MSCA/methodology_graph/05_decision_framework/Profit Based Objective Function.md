---
id: METH-DEC-005
title: "Profit Based Objective Function"
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
  - "methodology_idea.txt ('the objective being profit rather than yield, net of the water and input costs, since the whole point is that it should pay off')"
  - "prompt.txt §6 ('objective should be profit, not yield'; 'expected crop value - water cost - energy cost - input cost - operational cost')"
evidence_strength: source_grounded
confidence: high
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Counterfactual Irrigation Simulation]]"
downstream_nodes:
  - "[[Decision Recommendation Logic]]"
related_nodes:
  - "[[Prognostic Branch]]"
  - "[[Decision Engine Layer]]"
key_terms:
  - "[[Expected Profit]]"
  - "[[Expected Utility]]"
  - "[[Decision Regret]]"
  - "[[Irrigation Water Requirement]]"
risks: []
open_questions:
  - "RQ6: What is the decision objective (profit, water-use efficiency, yield stability, drought-risk reduction, or a weighted combination)?"
validation_needs:
  - "Confirm cost components and prices used in the objective for the pilot"
aliases:
  - "Profit objective"
  - "Economic objective function"
tags:
  - methodology-graph
  - decision
---

# Profit Based Objective Function

The scoring rule that ranks irrigation decisions by **expected economic return** — profit, not yield — netting out water, energy, input and operational costs.

## What it is

The objective that the decision engine optimizes is **profit rather than yield**. The PI states it directly: *"the objective being profit rather than yield, net of the water and input costs, since the whole point is that it should pay off"* (methodology_idea.txt). The analyst synthesis makes the same point and gives the explicit form (prompt.txt §6):

```
expected crop value − water cost − energy cost − input cost − operational cost
```

This is the **[[Expected Profit]]** computed across uncertain futures — the project-specific instance of **[[Expected Utility]]**. It is "expected" because each candidate decision's outcome is already averaged over the [[Weather Ensemble Scenario Evaluation]] before being scored here.

## Role in this methodology

This objective is what moves the project, in prompt.txt's words, *"from 'nice monitoring dashboard' to 'decision-support tool that can pay for itself'"* (prompt.txt §6). It takes the per-decision simulated outcomes produced by **[[Counterfactual Irrigation Simulation]]** and turns them into a single comparable economic score, which **[[Decision Recommendation Logic]]** then uses to choose. It is the economic core of the **[[Prognostic Branch]]** and is realised operationally in the **[[Decision Engine Layer]]** (the "economic objective function" component, prompt.txt §8).

The water-cost term connects directly to the physical **[[Irrigation Water Requirement]]**: how much water each decision implies feeds the cost side of the ledger. Because the objective ranks options, it also underpins notions of **[[Decision Regret]]** — how much economic value a chosen decision gave up versus the best option in hindsight.

## Open question

> [!warning] Decision needed — objective definition
> Whether the objective is **pure profit** or a **weighted combination** (profit, water-use efficiency, yield stability, drought-risk reduction) is **RQ6** in the [[Ten Research Questions]]. The sources are clear that **profit, not yield** is the headline principle, but the precise cost components, prices, and any multi-objective weighting are a **project decision** (hence `maturity: project_decision_needed`). Do not present specific price numbers as fixed — none are given in the sources.

## Source grounding

- "profit rather than yield, net of the water and input costs… it should pay off": `methodology_idea.txt`.
- "objective should be profit, not yield" and the `expected crop value − water − energy − input − operational cost` formula; "pay for itself": `prompt.txt §6`.

## Links & relationships

Upstream: [[Counterfactual Irrigation Simulation]]. Downstream: [[Decision Recommendation Logic]]. Related: [[Prognostic Branch]], [[Decision Engine Layer]]. Key terms: [[Expected Profit]], [[Expected Utility]], [[Decision Regret]], [[Irrigation Water Requirement]]. Hub: [[Methodology Graph - Meta Node]].
