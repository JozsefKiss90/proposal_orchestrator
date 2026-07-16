---
id: METH-INFRA-009
title: "Validation and Field Trial Layer"
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
  - "[[Source - Literature Review]]"
evidence_basis:
  - "prompt.txt §8 (Validation layer: field trials, sensor comparison, model accuracy, uncertainty calibration, decision-performance metrics)"
  - "prompt.txt §10 (RQ4 ground-truth, RQ5 uncertainty evaluation / 90% prediction intervals, RQ7 pilot success, RQ9 patch covariation)"
  - "litreview Report A §3.4 (few large-scale validation efforts with dense ground-truth networks)"
evidence_strength: source_grounded
confidence: medium
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Infrastructure Architecture]]"
downstream_nodes: []
related_nodes:
  - "[[Validation Risks]]"
  - "[[Control Stand Variant]]"
  - "[[Uncertainty Chain]]"
  - "[[Ten Research Questions]]"
key_terms:
  - "[[Ground Truth]]"
  - "[[Uncertainty Propagation]]"
risks:
  - "[[Validation Risks]]"
open_questions:
  - "RQ4 — what ground-truth measurements will be collected?"
  - "RQ5 — how will uncertainty be evaluated (e.g. do 90% prediction intervals contain the truth ~90% of the time)?"
  - "RQ7 — what counts as pilot success?"
  - "RQ9 — how will the homogeneous-patch / control-stand covariation be validated?"
validation_needs:
  - "A defined validation protocol, ground-truth network, and decision-performance metrics (currently open)"
aliases:
  - "Validation Layer"
tags:
  - methodology-graph
  - infrastructure
---

# Validation and Field Trial Layer

The layer that **tests whether the system actually works** in the field — through field trials, sensor comparison, model-accuracy checks, **uncertainty calibration**, and decision-performance metrics.

## What it is

In the layered infrastructure (prompt.txt §8), the **Validation layer** comprises *field trials, sensor comparison, model accuracy, uncertainty calibration, and decision-performance metrics*. This node is the home of all empirical checks that ground the methodology in reality, supplying the [[Ground Truth]] needed to train and validate the models and to verify the [[Uncertainty Chain]] end to end.

## Role in this methodology

Validation is where the methodology earns its credibility. Several of its checks map directly onto the project's open research questions:

- **Field trials & ground truth (RQ4).** What ground-truth measurements will be collected is still open; this layer would gather them and feed [[Ground Truth]] to both routes.
- **Uncertainty calibration (RQ5).** Because the red thread is uncertainty, validation must test calibration — e.g. *do 90% prediction intervals contain the true value about 90% of the time?* (prompt.txt §10). This is the empirical guarantee behind [[Uncertainty Propagation]] and the [[Uncertainty Chain]].
- **Decision-performance metrics (RQ7).** What counts as pilot success (better timing, water savings, profit increase, reduced stress-detection error) is a project decision; this layer would measure it.
- **Patch covariation validation (RQ9).** [[Route B - Homogeneous Patch Proxy]] and especially the [[Control Stand Variant]] *must* demonstrate that the proxy patch really covaries with the target crop; that proof is produced here.

## Source grounding

> [!note] Grounding
> The layer's components are from prompt.txt §8 (Validation layer). The 90%-prediction-interval calibration test, ground-truth, pilot-success and patch-covariation items are from the clarification questions in prompt.txt §10 (RQ4/RQ5/RQ7/RQ9). The state-of-the-art constraint — that *few large-scale validation efforts with dense ground-truth networks* exist — is from litreview Report A §3.4.

> [!warning] Open / unconfirmed (confidence: low on specifics)
> The **validation protocol, dataset, target field state, decision objective, and pilot success criteria are not defined in the sources** — they are open questions (RQ4, RQ5, RQ7, RQ9; see [[Ten Research Questions]]). This node names *what must be validated*, not a fixed protocol. No specific trial sites, crops, sample sizes, or success thresholds are asserted, as none appear in the sources.

The literature underlines why this layer matters: dense ground-truth validation networks are scarce, which is exactly the weakness the project must address (see [[Validation Risks]]).

## Links and relationships

- **Up:** [[Infrastructure Architecture]].
- **Validates:** the [[Uncertainty Chain]] (calibration) and the [[Control Stand Variant]] (covariation).
- **Risk:** [[Validation Risks]].
- **Open questions:** see [[Ten Research Questions]] (RQ4, RQ5, RQ7, RQ9).
