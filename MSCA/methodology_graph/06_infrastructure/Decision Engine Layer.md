---
id: METH-INFRA-008
title: "Decision Engine Layer"
node_type: infrastructure_layer
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
  - "prompt.txt §8 (Decision layer: irrigation recommendation engine, economic objective function, risk thresholds)"
  - "prompt.txt §6 (objective = profit not yield; expected crop value − water − energy − input − operational cost)"
  - "methodology_idea.txt (steer toward best expected end-of-season outcome; profit rather than yield)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[Decision Recommendation Logic]]"
  - "[[Profit Based Objective Function]]"
  - "[[Operational Decision Support Gap]]"
key_terms:
  - "[[Expected Profit]]"
  - "[[Decision Regret]]"
  - "[[Expected Utility]]"
risks:
  - "[[Operationalisation Risks]]"
open_questions: []
validation_needs:
  - "Decision-performance metrics and risk thresholds (RQ6 objective, RQ7 pilot success)"
aliases:
  - "Decision Layer"
  - "Irrigation Recommendation Engine"
tags:
  - methodology-graph
  - infrastructure
---

# Decision Engine Layer

The infrastructure layer that turns simulated counterfactual outcomes into an actual irrigation recommendation — hosting the **recommendation engine**, the **economic objective function**, and the **risk thresholds**.

## What it is

In the layered infrastructure (prompt.txt §8), the **Decision layer** comprises an *irrigation recommendation engine, economic objective function, and risk thresholds*. This node is the runtime home of the prognostic decision logic: it consumes the distribution of outcomes produced by [[Weather Ensemble Scenario Evaluation]] (via the [[AquaCrop Simulation Runtime]]) and applies the project's objective and risk rules to choose a recommended action. It is the operational counterpart of the decision-method nodes [[Decision Recommendation Logic]] and [[Profit Based Objective Function]].

## Role in this methodology

This layer is where the methodology delivers on its central promise: moving from *"a nice monitoring dashboard"* to *"a decision-support tool that can pay for itself"* (prompt.txt §6). Three responsibilities define it:

- **Economic objective function.** The source is explicit that the objective should be **profit, not yield** (methodology_idea.txt; prompt.txt §6): `expected crop value − water cost − energy cost − input cost − operational cost`. The engine evaluates each candidate decision against this [[Profit Based Objective Function]] in terms of [[Expected Profit]].
- **Recommendation engine.** It steers toward the decision with the **best expected end-of-season outcome** across uncertain futures, i.e. it ranks options by [[Expected Utility]] / expected profit and surfaces the winner (see [[Decision Recommendation Logic]]).
- **Risk thresholds.** Because outcomes are distributions, the engine must apply risk rules (and can reason about [[Decision Regret]] — how much worse a chosen decision turns out than the best possible one).

By providing exactly this kind of integrated recommendation engine, the layer is the project's response to the **operational gap** identified in the literature: the lack of operational frameworks that fuse all sensor types into real-time decision support (see [[Operational Decision Support Gap]]).

## Source grounding

> [!note] Grounding
> Components (recommendation engine, economic objective function, risk thresholds) are from prompt.txt §8. The profit-not-yield objective and its cost decomposition are from prompt.txt §6 and methodology_idea.txt. The "pay for itself" framing is from prompt.txt §6.

The precise **decision objective** (profit vs water-use efficiency vs yield stability vs drought-risk reduction, or a weighted combination) and what counts as **pilot success** are not fixed in the sources — they are open questions (RQ6, RQ7). The layer is therefore built to host a configurable objective rather than a fixed one.

## Links and relationships

- **Up:** [[Infrastructure Architecture]].
- **Implements:** [[Decision Recommendation Logic]] and [[Profit Based Objective Function]].
- **Addresses:** [[Operational Decision Support Gap]] (the SOTA gap this layer targets).
- **Risk:** [[Operationalisation Risks]].

*(Inference)* No specific solver, optimisation library, or rule engine is named in the sources, so none is asserted; implementation choice is a project decision.
