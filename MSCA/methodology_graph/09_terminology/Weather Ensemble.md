---
id: METH-TERM-014
title: "Weather Ensemble"
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
  - "prompt.txt §7"
  - "prompt.txt §6 (run each decision under multiple weather futures)"
  - "methodology_idea.txt (over weather ensembles)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Weather Ensemble Scenario Evaluation]]"
  - "[[Weather and Climate Data Layer]]"
key_terms:
  - "[[Counterfactual Simulation]]"
  - "[[Expected Utility]]"
risks: []
open_questions: []
validation_needs: []
aliases: []
tags:
  - methodology-graph
  - terminology
---

# Weather Ensemble

Multiple plausible future weather paths used to evaluate a decision under uncertainty rather than against a single forecast.

## Definition / What it is

A weather ensemble is a set of multiple plausible future weather paths (prompt.txt §7). Instead of committing to one forecast, the project considers a spread of possible futures so that decisions are judged across the weather uncertainty they will actually face.

## Role in this methodology

Each candidate irrigation decision is run forward "over weather ensembles" (methodology_idea.txt) — the model runs every candidate under multiple possible weather futures and compares expected outcomes (prompt.txt §6). This is implemented in [[Weather Ensemble Scenario Evaluation]] and draws its inputs (rainfall, temperature, evapotranspiration, radiation, wind) from the [[Weather and Climate Data Layer]]. Combined with [[Counterfactual Simulation]], the ensemble lets the system compute an [[Expected Utility]] (or expected profit) for each option averaged across uncertain futures, steering toward the choice with the best expected end-of-season result.

## Related

[[Weather Ensemble Scenario Evaluation]] · [[Weather and Climate Data Layer]] · [[Counterfactual Simulation]] · [[Expected Utility]]
