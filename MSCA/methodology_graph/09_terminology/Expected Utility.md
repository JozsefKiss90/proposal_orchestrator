---
id: METH-TERM-017
title: "Expected Utility"
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
  - "prompt.txt §7 (expected utility / expected profit: average value of a decision across uncertain futures)"
  - "prompt.txt §6"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Expected Profit]]"
  - "[[Decision Recommendation Logic]]"
key_terms:
  - "[[Decision Regret]]"
  - "[[Weather Ensemble]]"
risks: []
open_questions: []
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Expected Utility

The average value of a decision across uncertain futures — the general form of which expected profit is a specific, economic case.

## Definition / What it is

Expected utility is the average value of a decision across uncertain futures (prompt.txt §7, which pairs "expected utility / expected profit" together). It is the general criterion for choosing among options when outcomes are uncertain: weight each possible outcome by how likely it is, then prefer the option whose average value is highest.

## Role in this methodology

The project's concrete objective is [[Expected Profit]], the economic special case of expected utility (prompt.txt §6). Expected utility is computed by running each candidate decision over a [[Weather Ensemble]] and averaging outcomes (prompt.txt §6), and it is what [[Decision Recommendation Logic]] maximises when steering toward the best expected end-of-season result. It also frames the complementary notion of [[Decision Regret]] — how much worse a chosen option turned out compared with the best possible one after the fact. The precise objective (profit, water-use efficiency, yield stability, or a weighted combination) is an open project decision (RQ6).

## Related

[[Expected Profit]] · [[Decision Regret]] · [[Weather Ensemble]] · [[Decision Recommendation Logic]]
