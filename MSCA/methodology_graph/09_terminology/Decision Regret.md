---
id: METH-TERM-018
title: "Decision Regret"
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
evidence_basis:
  - "prompt.txt §7 (decision regret: how much worse a chosen decision was vs the best possible decision after the fact)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Decision Recommendation Logic]]"
  - "[[Profit Based Objective Function]]"
key_terms:
  - "[[Expected Utility]]"
risks: []
open_questions: []
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Decision Regret

How much worse a chosen decision turned out to be compared with the best possible decision, judged after the fact.

## Definition / What it is

Decision regret is how much worse a chosen decision was compared with the best possible decision, after the fact (prompt.txt §7). It is a retrospective, outcome-based measure: once the true weather and crop response are known, regret is the gap between what the chosen option delivered and what the best available option would have delivered.

## Role in this methodology

Regret is a natural complement to [[Expected Utility]] and [[Expected Profit]]: maximising expected value before the season aims to minimise expected regret. It gives [[Decision Recommendation Logic]] a risk-sensitive lens — a recommendation that performs acceptably across many futures may be preferred over one that is best on average but disastrous in some, controlling worst-case regret. It can also serve as an evaluation metric for the [[Profit Based Objective Function]], measuring how close the system's recommendations came to the best achievable decisions. The criteria that define pilot success against such measures remain an open project decision (RQ7).

## Related

[[Expected Utility]] · [[Decision Recommendation Logic]] · [[Profit Based Objective Function]]
