---
id: METH-DEC-003
title: "Counterfactual Irrigation Simulation"
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
  - "prompt.txt §6 (counterfactual: 'given the current estimated field state, what would happen under each possible decision?'; candidate-decision list)"
  - "methodology_idea.txt ('run the model forward under all the candidate decisions, over weather ensembles')"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[AquaCrop Decision Interface]]"
downstream_nodes:
  - "[[Decision Recommendation Logic]]"
related_nodes:
  - "[[Weather Ensemble Scenario Evaluation]]"
  - "[[Prognostic Branch]]"
  - "[[Profit Based Objective Function]]"
  - "[[AquaCrop Simulation Runtime]]"
key_terms:
  - "[[Counterfactual Simulation]]"
  - "[[Weather Ensemble]]"
  - "[[AquaCrop]]"
risks: []
open_questions: []
validation_needs:
  - "Confirm which candidate decisions are in scope for the pilot"
aliases:
  - "Counterfactual optimization"
tags:
  - methodology-graph
  - decision
---

# Counterfactual Irrigation Simulation

The prognostic step that asks, for the **current estimated field state**, *"what would happen under each possible irrigation decision?"* — running each candidate decision through the calibrated **[[AquaCrop]]** model.

## What it is

This is the **[[Counterfactual Simulation]]** core of the prognostic block. Once the [[AquaCrop Decision Interface]] holds a calibrated, uncertainty-bearing representation of the diagnosed state, the project runs the model **forward under all the candidate decisions** (methodology_idea.txt). The guiding question, from prompt.txt §6, is explicitly counterfactual: *"Given the current estimated field state, what would happen under each possible decision?"*

## Candidate decisions

The decision set named in the sources (prompt.txt §6) is:

| Candidate decision |
|---|
| No irrigation |
| Irrigate today |
| Irrigate in two days |
| Apply 10 mm / 20 mm / 30 mm water |
| Deficit irrigation |
| (Later) different fertilization strategies |

The PI's narrative scopes the first work to **irrigation**, with fertilization deferred — *"mainly with irrigation… fertilization can follow"* (methodology_idea.txt). So the fertilization options are flagged as later-stage, not pilot-stage.

> [!note] Scope note
> The exact subset of candidate decisions carried into the pilot is a design choice that follows from the broader scope questions (e.g. the decision objective, RQ6, and pilot success criteria, RQ7); it is not over-specified here beyond the source list.

## Role in this methodology

Counterfactual simulation is where monitoring becomes decision support. Each candidate decision is **not** run once: it is run under **[[Weather Ensemble Scenario Evaluation]]** so that every option is judged across multiple plausible weather futures rather than a single guessed forecast (methodology_idea.txt: *"over weather ensembles"*). The simulated end-of-season outcomes are then scored by the **[[Profit Based Objective Function]]** and resolved into a recommendation by **[[Decision Recommendation Logic]]**. Together these realise the **[[Prognostic Branch]]** of the [[Core Architecture]].

Execution of the forward runs is handled by the **[[AquaCrop Simulation Runtime]]**.

## Source grounding

- The counterfactual question and the full candidate-decision list: `prompt.txt §6`.
- "run the model forward under all the candidate decisions, over weather ensembles"; irrigation-first / fertilization-later scope: `methodology_idea.txt`.

## Links & relationships

Upstream: [[AquaCrop Decision Interface]]. Downstream: [[Decision Recommendation Logic]]. Related: [[Weather Ensemble Scenario Evaluation]], [[Prognostic Branch]], [[Profit Based Objective Function]], [[AquaCrop Simulation Runtime]]. Key terms: [[Counterfactual Simulation]], [[Weather Ensemble]], [[AquaCrop]]. Hub: [[Methodology Graph - Meta Node]].
