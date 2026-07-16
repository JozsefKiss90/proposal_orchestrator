---
id: METH-INFRA-006
title: "Probabilistic Modelling Runtime"
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
  - "prompt.txt §8 (Modelling layer: probabilistic fusion model, uncertainty estimation, AquaCrop calibration, scenario simulation)"
  - "prompt.txt §3 (Bayesian hierarchical model, Gaussian process, probabilistic ML; rigorous but demanding compute)"
  - "methodology_idea.txt (Route 1 leans heavily on ML; uncertainty-aware calibration, doi:10.1016/j.envsoft.2022.105556)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Uncertainty Aware AquaCrop Calibration]]"
  - "[[Uncertainty Chain]]"
  - "[[Model Complexity Risks]]"
key_terms:
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Posterior Distribution]]"
  - "[[Uncertainty Propagation]]"
risks:
  - "[[Model Complexity Risks]]"
open_questions: []
validation_needs:
  - "Compute budget, modelling expertise and reproducibility tooling sufficient for probabilistic fusion at field scale (see RQ5 uncertainty calibration)"
aliases:
  - "Modelling Layer"
tags:
  - methodology-graph
  - infrastructure
---

# Probabilistic Modelling Runtime

The compute and software layer that runs the project's **probabilistic fusion model**, produces **uncertainty estimates**, and supports **uncertainty-aware model calibration** — the engine room of the diagnostic side of the methodology.

## What it is

In the layered infrastructure picture (prompt.txt §8), the **Modelling layer** is described as comprising a *probabilistic fusion model, uncertainty estimation, AquaCrop calibration, and scenario simulation*. This node covers the first three (probabilistic fusion + uncertainty estimation, plus the calibration of process models with retained uncertainty); the simulation-execution part is treated separately under [[AquaCrop Simulation Runtime]]. It is the runtime where [[Route A - Direct Probabilistic Fusion]] would actually be trained and run, and where the [[Uncertainty Aware AquaCrop Calibration]] method is executed.

## Role in this methodology

This runtime is where the **red thread of uncertainty** is computationally honoured. The diagnostic block must output not just a point estimate of the [[Latent Field State]] but a full [[Posterior Distribution]], so the runtime must support probabilistic model families. The source narrative (prompt.txt §3) names three candidate model classes that this layer must be able to host:

- [[Bayesian Hierarchical Model]] — estimating field-level effects together with general crop/soil/weather relationships, with explicit uncertainty ranges.
- [[Gaussian Process]] — spatial / spatio-temporal prediction returning a value *and* an uncertainty surface.
- [[Probabilistic Machine Learning]] — any ML approach that returns distributions or confidence intervals rather than point predictions.

The same layer hosts the PI's **uncertainty-aware calibration** of the crop model (methodology_idea.txt; doi:10.1016/j.envsoft.2022.105556), which retains parameter uncertainty rather than collapsing to one overconfident parameter set. In this way the runtime is the upstream guarantor of the [[Uncertainty Chain]]: every quantity it emits carries an explicit uncertainty that downstream layers must respect and propagate (see [[Uncertainty Propagation]]).

## Source grounding

> [!note] Grounding
> The layer and its components are taken directly from prompt.txt §8 (Modelling layer) and §3 (the three probabilistic model families and the statement that Route 1 is "rigorous but demanding... needs strong modelling expertise, good validation data, and careful computational design"). The methodology_idea.txt narrative confirms Route 1 "leans heavily on ML" and ties the calibration to the PI's prior DOI.

The source itself flags that this is the **demanding** part of the project: it "needs strong modelling expertise, good validation data, and careful computational design" (prompt.txt §3). That cost and complexity is captured as [[Model Complexity Risks]] — overconfidence, expertise burden, and compute load are all real threats to this layer.

## Links and relationships

- **Up:** [[Infrastructure Architecture]] (the layered hub).
- **Drives:** [[Route A - Direct Probabilistic Fusion]] (the modelling route this runtime executes) and [[Uncertainty Aware AquaCrop Calibration]].
- **Feeds:** the [[Uncertainty Chain]] — its posteriors are the first link in the end-to-end propagation.
- **Risk:** [[Model Complexity Risks]].

*(Inference)* No fabricated framework, language, hardware, or cloud platform is specified here because the sources name none; concrete tooling choices remain a project decision.
