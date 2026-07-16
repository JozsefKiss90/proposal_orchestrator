---
id: METH-RISK-005
title: "Model Complexity Risks"
node_type: risk
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
  - "[[Source - Literature Review]]"
evidence_basis:
  - "prompt.txt §3 (Route A rigorous but demanding: expertise, validation data, compute)"
  - "methodology_idea.txt (hardcore route leans on ML; overconfidence vs honest range)"
  - "litreview Report A §3.4 (sensor calibration/integration complexity)"
  - "doi:10.1016/j.envsoft.2022.105556 (retain parameter uncertainty)"
evidence_strength: source_grounded
confidence: medium
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Risk Register]]"
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Uncertainty Aware AquaCrop Calibration]]"
  - "[[Probabilistic Modelling Runtime]]"
  - "[[Risk Register]]"
key_terms:
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Uncertainty Propagation]]"
risks: []
open_questions:
  - "RQ2 — both routes, or one main + one fallback?"
  - "[[Ten Research Questions]]"
validation_needs:
  - "Confirm modelling capacity, compute budget and fallback strategy"
aliases: []
tags:
  - methodology-graph
  - risk
---

# Model Complexity Risks

Risks arising from the demanding probabilistic-modelling core: Route A's expertise/compute burden, the danger of overconfidence, and sensor calibration complexity.

These risks are **source-grounded**. The analyst synthesis describes [[Route A - Direct Probabilistic Fusion]] as rigorous but demanding, needing **strong modelling expertise, good validation data and careful compute** (prompt.txt §3); the methodology narrative calls it the "hardcore" road that "leans heavily on the machine learning side" and "wants strong hands" (methodology_idea.txt). This node feeds the [[Risk Register]] and is the risk view of the [[Probabilistic Modelling Runtime]].

## The risks

### 1. Route A modelling burden
Direct one-step probabilistic fusion via a [[Bayesian Hierarchical Model]], [[Gaussian Process]] or other [[Probabilistic Machine Learning]] demands scarce expertise, ample validation data and non-trivial compute (prompt.txt §3). If any is short, the rigorous route stalls. This is why **RQ2** (both routes, or one main + one fallback) matters: [[Route B - Homogeneous Patch Proxy]] is the credible lighter fallback.

### 2. Overconfidence
The narrative warns against collapsing to "one overconfident parameter set" instead of keeping an honest range; the PI's [[Uncertainty Aware AquaCrop Calibration]] method (doi:10.1016/j.envsoft.2022.105556) exists precisely to **retain parameter uncertainty** (methodology_idea.txt). If uncertainty is understated, the [[Uncertainty Propagation]] red thread breaks and the decision engine is fed false confidence.

### 3. Sensor calibration / integration complexity
The review lists **sensor calibration/integration complexity** as a persistent challenge (litreview Report A §3.4). Integrating radar, optical, soil and weather streams correctly is itself an error source that can propagate into the fused state.

> [!note] Compute is a real but addressable constraint
> The [[Probabilistic Modelling Runtime]] is the infrastructure answer to the compute side of this risk; it must be provisioned for probabilistic fusion and uncertainty estimation.

## Mitigations (proposal-level)
- Keep [[Route B - Homogeneous Patch Proxy]] as a credible fallback; stage Route A's build (RQ2).
- Use uncertainty-aware calibration to avoid overconfidence (retain a parameter range).
- Provision the [[Probabilistic Modelling Runtime]]; build a QC pipeline for sensor integration.

## Links and relationships
This node rolls up to the [[Risk Register]] and the [[Methodology SWOT Matrix]] weaknesses (Route A ML burden) and threats (overconfidence). It is bound to [[Route A - Direct Probabilistic Fusion]], the [[Uncertainty Aware AquaCrop Calibration]] and the [[Probabilistic Modelling Runtime]]; its open item maps to RQ2 in the [[Ten Research Questions]].
