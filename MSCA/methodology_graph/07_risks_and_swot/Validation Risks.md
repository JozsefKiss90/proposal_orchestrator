---
id: METH-RISK-003
title: "Validation Risks"
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
  - "[[Source - Literature Review]]"
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "litreview Report A key limitations (few large-scale validation with dense ground-truth)"
  - "litreview Report A Open Research Questions (cost-effective ground-truth networks)"
  - "methodology_idea.txt (patch covariation must be measured, not assumed)"
  - "prompt.txt §1 (uncertainty honest), §4 (Route B needs validation)"
evidence_strength: source_grounded
confidence: medium
maturity: project_decision_needed
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Risk Register]]"
downstream_nodes: []
related_nodes:
  - "[[Validation and Field Trial Layer]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Control Stand Variant]]"
  - "[[Risk Register]]"
  - "[[Ten Research Questions]]"
key_terms:
  - "[[Ground Truth]]"
  - "[[Uncertainty Propagation]]"
risks: []
open_questions:
  - "RQ4 — what ground-truth measurements will be collected?"
  - "RQ5 — how will uncertainty be evaluated (e.g. 90% PI coverage)?"
  - "RQ9 — how will patch/control-stand covariation be validated?"
  - "[[Ten Research Questions]]"
validation_needs:
  - "Define ground-truth protocol, uncertainty-calibration metric, and covariation test before commitment"
aliases: []
tags:
  - methodology-graph
  - risk
---

# Validation Risks

Risks that the methodology cannot be credibly validated: insufficient dense ground truth, an unproven patch-covariation assumption, and uncalibrated uncertainty.

These risks are **source-grounded**. The literature review (Report A) lists "few large-scale validation efforts using both remote sensing outputs AND dense ground-truth networks" as a key limitation, and its Open Research Questions call specifically for *cost-effective ground-truth networks to validate large-scale multi-sensor frameworks* (litreview Report A). The methodology narrative makes validation central: the project "lives or dies" on fusion, modelling and validation, and keeping uncertainty honest is "the heart of the whole thing" (methodology_idea.txt; prompt.txt §1). This node feeds the [[Risk Register]] and is implemented through the [[Validation and Field Trial Layer]].

## The risks

### 1. Sparse / under-powered ground truth
The field is short on large-scale validation with dense ground-truth networks (litreview Report A key limitations). Without enough ground truth, neither the diagnostic field state nor decision performance can be defended. This is the hazard behind the [[Ground Truth]] concept and is open as **RQ4** (what measurements will be collected).

### 2. Unproven patch covariation (Route B)
[[Route B - Homogeneous Patch Proxy]] sidesteps the resolution problem by leaning on a nearby patch whose biology covaries with the chosen crop. As the narrative warns, similar conditions are *assumed* to give similar effect; the [[Control Stand Variant]] exists precisely so we can *measure* the covariation rather than assume it (methodology_idea.txt; prompt.txt §4). If the covariation is weak or context-specific, Route B's diagnostic loses its basis. Open as **RQ9**.

### 3. Uncertainty miscalibration
The whole premise is honest uncertainty travelling into the decision via the [[Uncertainty Chain]] and [[Uncertainty Propagation]]. If predicted intervals are not calibrated (e.g. 90% prediction intervals do not contain the truth roughly 90% of the time), the probabilistic outputs mislead the decision engine. Open as **RQ5**, to be evaluated in the [[Validation and Field Trial Layer]].

> [!warning] Decisions still open
> The validation protocol, the target field state, ground-truth measurements, the uncertainty-calibration metric and the covariation test are not yet fixed in the sources (RQ3, RQ4, RQ5, RQ7, RQ9). `maturity: project_decision_needed`; severity cannot be finalised until these are defined. See [[Ten Research Questions]].

## Mitigations (proposal-level)
- Plan field trials and a cost-effective dense ground-truth network early (addresses RQ4).
- Pre-register a covariation test for Route B / the control stand (RQ9).
- Adopt explicit uncertainty-calibration metrics (e.g. PI coverage) in the validation layer (RQ5).

## Links and relationships
This node rolls up to the [[Risk Register]] and the [[Methodology SWOT Matrix]] (weaknesses: covariation assumption, validation-data needs). It is the risk view of the [[Validation and Field Trial Layer]] and is tightly bound to [[Route B - Homogeneous Patch Proxy]], the [[Control Stand Variant]] and [[Ground Truth]].
