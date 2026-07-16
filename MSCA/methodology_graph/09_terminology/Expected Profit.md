---
id: METH-TERM-016
title: "Expected Profit"
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
  - "prompt.txt §6 (objective should be profit, not yield)"
  - "prompt.txt §7"
  - "methodology_idea.txt (profit rather than yield, net of water and input costs)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Profit Based Objective Function]]"
  - "[[Decision Engine Layer]]"
  - "[[Decision Recommendation Logic]]"
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

# Expected Profit

The average net economic value of a decision across uncertain futures — crop value minus costs, averaged over the weather and model uncertainty.

## Definition / What it is

Expected profit is the average value of a decision across uncertain futures (prompt.txt §7), where value is measured economically: `expected crop value − water cost − energy cost − input cost − operational cost` (prompt.txt §6). The colleague is explicit that the objective should be profit, not yield — net of water and input costs, "since the whole point is that it should pay off" (methodology_idea.txt).

## Role in this methodology

Expected profit is the objective the decision step optimises. It is formalised in the [[Profit Based Objective Function]], computed inside the [[Decision Engine Layer]], and applied by [[Decision Recommendation Logic]] to steer toward the candidate decision with the best expected end-of-season outcome. It is the concrete economic instance of [[Expected Utility]]; choosing profit over yield is what moves the project from a "nice monitoring dashboard" to a "decision-support tool that can pay for itself" (prompt.txt §6). The exact decision objective remains an open project choice (RQ6).

## Related

[[Profit Based Objective Function]] · [[Expected Utility]] · [[Decision Engine Layer]] · [[Decision Recommendation Logic]]
