---
id: METH-CORE-003
title: "Prognostic Branch"
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
  - "methodology_idea.txt (prognostic branch with counterfactuals; run forward over weather ensembles; profit not yield)"
  - "prompt.txt §1 (Prognostic block: what happens under option A/B/C → select best)"
  - "prompt.txt §6 (counterfactual optimization; candidate decisions; profit objective)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[AquaCrop Decision Interface]]"
  - "[[Diagnostic Branch]]"
downstream_nodes:
  - "[[Decision Recommendation Logic]]"
related_nodes:
  - "[[Counterfactual Irrigation Simulation]]"
  - "[[Weather Ensemble Scenario Evaluation]]"
  - "[[Profit Based Objective Function]]"
  - "[[Uncertainty Chain]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Counterfactual Simulation]]"
  - "[[Weather Ensemble]]"
  - "[[Expected Profit]]"
  - "[[Expected Utility]]"
  - "[[Decision Regret]]"
risks: []
open_questions:
  - "Decision objective: profit, water-use efficiency, yield stability, or weighted combination? (RQ6)"
  - "What counts as pilot success? (RQ7)"
validation_needs:
  - "Decision-performance metrics (RQ7)"
aliases:
  - "Prognostic Block"
tags:
  - methodology-graph
  - core
---

# Prognostic Branch

The prognostic branch is the "what happens next" half of the [[Core Architecture]]: starting from the diagnosed field state, it simulates what would happen under each candidate irrigation decision and selects the option with the best expected outcome at the end of the season.

## What it is

The PI narrative defines this as the second branch, *"prognostic, with counterfactuals: given that state, what would happen under the different decisions, so that we can pick the best one"* (methodology_idea.txt). The analyst synthesis calls it the **Prognostic block** — *"what will happen if we choose irrigation option A, B, C?"* — whose role is to *"run future scenarios and select the best decision"* (prompt.txt §1).

The decision principle is explicitly **counterfactual** (prompt.txt §6): *"given the current estimated field state, what would happen under each possible decision?"* This is the heart of [[Counterfactual Simulation]], realised in this graph by [[Counterfactual Irrigation Simulation]].

## Role in this methodology

The branch takes the diagnosed state from the [[Diagnostic Branch]] and operates through the [[AquaCrop Decision Interface]], which "stands for the plant" and is the interface through which decisions act (methodology_idea.txt). Each candidate decision is run forward, and the branch hands its scored options to the [[Decision Recommendation Logic]].

Candidate decisions enumerated in the source (prompt.txt §6) include: no irrigation; irrigate today; irrigate in two days; apply 10 / 20 / 30 mm of water; deficit irrigation; and, later, different fertilization strategies.

## Running over uncertain futures

Crucially, each candidate decision is run *"under all the candidate decisions, over weather ensembles"* (methodology_idea.txt) — see [[Weather Ensemble Scenario Evaluation]] and the [[Weather Ensemble]] concept. The branch then *"compares expected outcomes"* (prompt.txt §6) and steers toward *"the one with the best expected outcome at the end of the season."* This makes the branch a natural carrier of the [[Uncertainty Chain]]: weather and model uncertainty are folded into the comparison rather than ignored.

## Profit, not yield

The source is emphatic that *"the objective should be profit, not yield"* (prompt.txt §6; methodology_idea.txt: profit *"net of the water and input costs, since the whole point is that it should pay off"*). The scoring criterion is therefore [[Expected Profit]] — formalised by the [[Profit Based Objective Function]] as `expected crop value − water cost − energy cost − input cost − operational cost` — a special case of [[Expected Utility]]. Comparing the chosen option against the best possible one after the fact is the basis of [[Decision Regret]].

## Source grounding

- Branch / block definition and "select the best decision": `methodology_idea.txt`, `prompt.txt §1`.
- Counterfactual principle and candidate-decision list: `prompt.txt §6`.
- Run over weather ensembles, best expected end-of-season outcome, profit-not-yield: `methodology_idea.txt`, `prompt.txt §6`.

## Links and relationships

Up: [[AquaCrop Decision Interface]] · [[Diagnostic Branch]]. Down: [[Decision Recommendation Logic]]. Related: [[Counterfactual Irrigation Simulation]] · [[Weather Ensemble Scenario Evaluation]] · [[Profit Based Objective Function]] · [[Uncertainty Chain]]. Hub: [[Methodology Graph - Meta Node]].

## Open questions

The decision objective (profit vs water-use efficiency vs yield stability vs a weighted combination) is a project decision (RQ6), and what counts as pilot success — better timing, water savings, profit increase, reduced stress-detection error — is still open (RQ7). See [[Ten Research Questions]].
