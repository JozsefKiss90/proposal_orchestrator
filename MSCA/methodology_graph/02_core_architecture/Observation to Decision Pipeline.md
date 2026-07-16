---
id: METH-CORE-005
title: "Observation to Decision Pipeline"
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
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "prompt.txt §1 (pipeline string: sensors → probabilistic diagnosis → calibration → counterfactuals → recommendation)"
  - "prompt.txt §8 (infrastructure layers feeding the pipeline)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Core Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[Earth Observation Layer]]"
  - "[[Ground Sensing Layer]]"
  - "[[Weather and Climate Data Layer]]"
  - "[[Diagnostic Branch]]"
  - "[[AquaCrop Decision Interface]]"
  - "[[Prognostic Branch]]"
  - "[[Decision Recommendation Logic]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Latent Field State]]"
  - "[[Counterfactual Simulation]]"
  - "[[Expected Profit]]"
risks: []
open_questions:
  - "Target field state (RQ3); decision objective (RQ6) — see [[Ten Research Questions]]"
validation_needs: []
aliases:
  - "End-to-End Pipeline"
  - "Observation-to-Decision Pipeline"
tags:
  - methodology-graph
  - core
---

# Observation to Decision Pipeline

The observation-to-decision pipeline is the linear stage chain that operationalises the [[Core Architecture]]: it traces a single path from raw multi-source observations, through probabilistic diagnosis and model calibration, to counterfactual simulation and a final irrigation recommendation.

## What it is

The analyst synthesis states the pipeline as a single string (prompt.txt §1):

> [!note] Pipeline (prompt.txt §1)
> Satellite + soil sensors + weather + field observations → probabilistic field-state diagnosis → uncertainty-aware AquaCrop calibration → counterfactual irrigation simulations → profit/risk-based recommendation.

Where the [[Core Architecture]] presents the *two-block* (diagnostic + prognostic) decomposition, this node presents the same method as a *sequence of stages* — a complementary, linear view useful for mapping each stage onto a concrete infrastructure layer. *(This stage-by-stage rendering is a synthesis view of the same source pipeline, not a new claim.)*

## The stages

| # | Stage | What happens | Graph node(s) |
|---|---|---|---|
| 1 | Observation | Collect satellite, soil-sensor, weather and field-observation streams | [[Earth Observation Layer]], [[Ground Sensing Layer]], [[Weather and Climate Data Layer]] |
| 2 | Diagnosis | Fuse inputs into a probabilistic estimate of the [[Latent Field State]] | [[Diagnostic Branch]] |
| 3 | Calibration | Calibrate AquaCrop in an uncertainty-aware way; use it as the decision interface | [[AquaCrop Decision Interface]] |
| 4 | Counterfactuals | Simulate each candidate decision over uncertain futures | [[Prognostic Branch]] |
| 5 | Recommendation | Select the option with the best expected economic outcome | [[Decision Recommendation Logic]] |

## Role in this methodology

The pipeline is the connective tissue between the infrastructure and the science. Stage 1 draws on the [[Earth Observation Layer]], [[Ground Sensing Layer]] and [[Weather and Climate Data Layer]]; these feed [[Data Fusion]] in the [[Diagnostic Branch]] (stage 2), producing the [[Latent Field State]]. That state passes into the [[AquaCrop Decision Interface]] (stage 3), which both "stands for the plant" and is the interface through which decisions act (methodology_idea.txt). [[Counterfactual Simulation]] in the [[Prognostic Branch]] (stage 4) scores each option, and the [[Decision Recommendation Logic]] (stage 5) returns the choice maximising [[Expected Profit]].

Although shown as a clean sequence, the pipeline carries uncertainty across every stage — the diagnostic step exports a distribution, not a point — so it should be read together with the [[Uncertainty Chain]]. The diagnostic stage itself may be implemented via either [[Route A - Direct Probabilistic Fusion]] or [[Route B - Homogeneous Patch Proxy]]; from the diagnosed state onward the path is identical for both (methodology_idea.txt).

## Source grounding

- The five-stage pipeline string: `prompt.txt §1`.
- The mapping of stages onto Earth-observation / ground-sensing / data-platform / modelling / decision layers: `prompt.txt §8`.

## Links and relationships

Up: [[Core Architecture]]. Related: [[Earth Observation Layer]] · [[Ground Sensing Layer]] · [[Weather and Climate Data Layer]] · [[Diagnostic Branch]] · [[AquaCrop Decision Interface]] · [[Prognostic Branch]] · [[Decision Recommendation Logic]]. Hub: [[Methodology Graph - Meta Node]].

## Open questions

The exact content of stage 2's "field state" (RQ3) and stage 5's objective (RQ6) remain project decisions — see [[Ten Research Questions]].
