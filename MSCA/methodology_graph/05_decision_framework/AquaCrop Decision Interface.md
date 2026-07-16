---
id: METH-DEC-001
title: "AquaCrop Decision Interface"
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
  - "methodology_idea.txt (AquaCrop: 'stands for the plant' AND 'interface through which the decisions act')"
  - "prompt.txt §5 (AquaCrop = FAO crop-growth model; yield response to water; bridge monitoring→decision)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Diagnostic Branch]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
downstream_nodes:
  - "[[Counterfactual Irrigation Simulation]]"
  - "[[Prognostic Branch]]"
related_nodes:
  - "[[Uncertainty Aware AquaCrop Calibration]]"
  - "[[AquaCrop Simulation Runtime]]"
key_terms:
  - "[[AquaCrop]]"
  - "[[Evapotranspiration]]"
  - "[[Crop Water Stress]]"
  - "[[Irrigation Water Requirement]]"
  - "[[Root Zone Soil Moisture]]"
risks: []
open_questions:
  - "RQ1: Is the first crop definitely tomato, or more broadly horticultural row crops? (tomato tentative — unconfirmed)"
validation_needs:
  - "Confirm AquaCrop calibration adequacy for the chosen horticultural row crop"
aliases:
  - "AquaCrop bridge"
  - "Decision simulator"
tags:
  - methodology-graph
  - decision
---

# AquaCrop Decision Interface

The point in the methodology where a calibrated **[[AquaCrop]]** crop-growth model takes the diagnosed field state and turns it into a decision simulator — it both *stands for the plant* and is the *interface through which irrigation decisions act*.

## What it is

[[AquaCrop]] is the FAO crop-growth model that simulates **yield response to water**, and is especially suited to situations where **water is the limiting factor** (prompt.txt §5). In this methodology it does not replace the remote-sensing diagnosis; it sits downstream of it. The PI's design narrative gives [[AquaCrop]] a dual job: it **"stands for the plant"** (a physically grounded surrogate for crop growth and water use) **and** it is the **"interface through which the decisions act"** (methodology_idea.txt). That dual role is why this node is the hinge between the diagnostic and prognostic halves of the [[Core Architecture]].

## Role in this methodology

The model is the **bridge from monitoring to decision-making** (prompt.txt §5). It receives the probabilistic estimate of the [[Latent Field State]] produced by the [[Diagnostic Branch]] — whichever route generated it, **[[Route A - Direct Probabilistic Fusion]]** or **[[Route B - Homogeneous Patch Proxy]]** — and provides the simulation substrate for the [[Prognostic Branch]]. Concretely, [[AquaCrop]] is what lets the project ask *"what if we irrigate today? delay? apply less water? if water/input costs are high? if the coming weather is dry/wet/hot?"* (prompt.txt §5). Those questions become the **[[Counterfactual Irrigation Simulation]]** runs that feed downstream decision logic.

[[AquaCrop]] reasons in the natural quantities of the water-limited regime: it tracks **[[Evapotranspiration]]**, the **[[Irrigation Water Requirement]]**, **[[Root Zone Soil Moisture]]**, and the resulting **[[Crop Water Stress]]** and yield. The execution of calibration and scenario runs is described in **[[AquaCrop Simulation Runtime]]**.

Crucially, [[AquaCrop]] enters the methodology's "red thread" of uncertainty through **[[Uncertainty Aware AquaCrop Calibration]]**: rather than collapsing to one overconfident parameter set, calibration keeps an honest parameter range so that the field-state uncertainty arriving from the diagnostic branch is not discarded at the model boundary (methodology_idea.txt).

## Scope

The PI's narrative scopes the first application to **horticulture, mainly irrigation**, which is *exactly where [[AquaCrop]] is strong*; fertilization can follow later (methodology_idea.txt). The specific first crop is not firmly fixed.

> [!warning] Unconfirmed — first crop
> The PI writes *"do I remember right, that it would be tomato first?"* (methodology_idea.txt), i.e. **tomato is tentative**. The safe framing is **horticultural row crops**. This is RQ1 in the [[Ten Research Questions]]; do not present tomato as decided. `confidence: low` applies to the crop choice only; the AquaCrop interface role itself is `source_grounded`.

## Source grounding

- Dual role ("stands for the plant" + decision interface) and the horticulture/irrigation-first scope: `methodology_idea.txt`.
- AquaCrop as FAO yield-response-to-water model, water-limiting suitability, and "bridge from monitoring to decision-making" / decision-simulator framing: `prompt.txt §5`.

## Links & relationships

Upstream: [[Diagnostic Branch]], [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]]. Downstream: [[Counterfactual Irrigation Simulation]], [[Prognostic Branch]]. Related: [[Uncertainty Aware AquaCrop Calibration]], [[AquaCrop Simulation Runtime]]. See also the [[Core Architecture]] and the [[Methodology Graph - Meta Node]].
