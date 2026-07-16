---
id: METH-INFRA-007
title: "AquaCrop Simulation Runtime"
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
  - "prompt.txt §8 (Modelling layer: AquaCrop calibration, scenario simulation)"
  - "prompt.txt §5 (AquaCrop as decision simulator; FAO yield-response-to-water model)"
  - "prompt.txt §6 (run each candidate decision under multiple weather futures)"
  - "methodology_idea.txt (calibrate a simple AquaCrop model; run forward under all candidate decisions over weather ensembles)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[AquaCrop Decision Interface]]"
  - "[[Counterfactual Irrigation Simulation]]"
  - "[[Weather Ensemble Scenario Evaluation]]"
key_terms:
  - "[[AquaCrop]]"
  - "[[Counterfactual Simulation]]"
  - "[[Weather Ensemble]]"
risks: []
open_questions: []
validation_needs:
  - "Throughput to run many candidate decisions × weather ensemble members per decision point"
aliases:
  - "Scenario Simulation Runtime"
tags:
  - methodology-graph
  - infrastructure
---

# AquaCrop Simulation Runtime

The execution layer that **calibrates AquaCrop** and runs its forward **scenario simulations** — the compute that turns a diagnosed field state into counterfactual irrigation futures.

## What it is

Within the layered infrastructure (prompt.txt §8), the **Modelling layer** lists *AquaCrop calibration* and *scenario simulation* among its components. This node isolates that execution responsibility: the runtime that physically runs [[AquaCrop]] — first to calibrate it (uncertainty-aware), then to drive the forward, what-if simulations defined by the [[AquaCrop Decision Interface]]. It is the operational counterpart of the decision-method nodes [[Counterfactual Irrigation Simulation]] and [[Weather Ensemble Scenario Evaluation]].

## Role in this methodology

The methodology gives AquaCrop a dual role: it *"stands for the plant"* and is *"the interface through which decisions act"* (methodology_idea.txt). The simulation runtime is what makes this concrete and repeatable. For every decision point the system must (methodology_idea.txt; prompt.txt §6):

- run AquaCrop **forward under all candidate decisions** (no irrigation; irrigate today; irrigate in two days; apply 10/20/30 mm; deficit irrigation; later, fertilization strategies), and
- run each of those candidates **over a [[Weather Ensemble]]** of plausible future weather paths.

This is a combinatorial workload — candidate decisions × ensemble members — so the runtime's purpose is to execute many [[Counterfactual Simulation]] runs efficiently and collect their outcomes for the prognostic comparison. AquaCrop is well-suited to this because, as the FAO model of **yield response to water**, it is *"especially suited to situations where water is a limiting factor"* (prompt.txt §5), which is exactly the irrigation-focused scope of the project.

## Source grounding

> [!note] Grounding
> AquaCrop's identity (FAO crop-growth model simulating yield response to water; the "decision simulator" that asks what-if-we-irrigate-today / delay / apply-less / prices-high / weather-dry-wet-hot) is from prompt.txt §5. The forward-under-all-decisions-over-weather-ensembles workload is from prompt.txt §6 and methodology_idea.txt. The layer placement is from prompt.txt §8.

The calibration that this runtime executes is the **uncertainty-aware** one: see [[AquaCrop Decision Interface]] and (for the method itself) [[Uncertainty Aware AquaCrop Calibration]]. The runtime must therefore carry forward calibrated *parameter ranges*, not a single parameter set, so that simulated outcomes themselves remain probabilistic.

## Links and relationships

- **Up:** [[Infrastructure Architecture]].
- **Executes:** [[Counterfactual Irrigation Simulation]] and [[Weather Ensemble Scenario Evaluation]] against the [[AquaCrop Decision Interface]].
- **Models:** [[AquaCrop]] (the underlying FAO model).

*(Inference)* The sources do not specify a particular AquaCrop implementation, engine version, or compute substrate, so none is asserted here; tooling is a project decision.
