---
id: METH-TERM-013
title: "Counterfactual Simulation"
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
  - "prompt.txt §6 (counterfactual optimization)"
  - "methodology_idea.txt (run forward under all candidate decisions)"
evidence_strength: source_grounded
confidence: high
maturity: concept
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Counterfactual Irrigation Simulation]]"
  - "[[Prognostic Branch]]"
key_terms:
  - "[[AquaCrop]]"
  - "[[Weather Ensemble]]"
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Counterfactual"
tags:
  - methodology-graph
  - terminology
---

# Counterfactual Simulation

A "what would happen if…" scenario run through the model — asking how the system would respond under a decision that has not (yet) been taken.

## Definition / What it is

A counterfactual is a "what would happen if…" scenario (prompt.txt §7). In this project it is the engine of the prognostic step: given the current estimated field state, the model asks what would happen under each possible decision (prompt.txt §6).

## Role in this methodology

Counterfactual simulation is realised concretely in [[Counterfactual Irrigation Simulation]], which sits inside the [[Prognostic Branch]]. The calibrated [[AquaCrop]] model is run forward under all candidate decisions — no irrigation, irrigate today, irrigate in two days, apply 10/20/30 mm, deficit irrigation — and, later, fertilization strategies (prompt.txt §6; methodology_idea.txt). Each candidate is evaluated across a [[Weather Ensemble]] of plausible futures so the comparison reflects weather uncertainty, and the option with the best expected end-of-season outcome is selected (methodology_idea.txt). This is what turns the system from a monitoring dashboard into a decision-support tool.

## Related

[[Counterfactual Irrigation Simulation]] · [[Prognostic Branch]] · [[AquaCrop]] · [[Weather Ensemble]]
