---
id: METH-ROUTE-003
title: "Control Stand Variant"
node_type: methodology_route
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
  - "methodology_idea.txt (seed idea: deliberately plant a control stand of a covarying species -> hands us homogeneity, lets us measure covariation instead of assuming it)"
  - "prompt.txt §4 (experimental version = a 'designed proxy sensor'; needs validation)"
evidence_strength: source_grounded
confidence: medium
maturity: concept
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes:
  - "[[Route B - Homogeneous Patch Proxy]]"
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Validation and Field Trial Layer]]"
  - "[[Ground Sensing Layer]]"
key_terms:
  - "[[Covariate]]"
  - "[[Ground Truth]]"
  - "[[Crop Water Stress]]"
risks:
  - "[[Validation Risks]]"
open_questions:
  - "How will the control-stand covariation with the target crop be validated scientifically? (RQ9)"
validation_needs:
  - "Demonstrate measured (not assumed) covariation between the control stand and the target crop"
aliases:
  - "Designed proxy sensor"
  - "Control stand"
tags:
  - methodology-graph
  - route
---

# Control Stand Variant

A "seed idea" extending [[Route B - Homogeneous Patch Proxy]]: instead of only *searching* for a covarying patch, deliberately **plant** a control stand of a covarying species so its covariation with the target crop can be measured rather than assumed.

## What it is

The design narrative offers this "just a seed for now": "instead of only searching for such a patch, we could deliberately plant a control stand of a covarying species, which would hand us the homogeneity and let us measure the covariation instead of assuming it." The analyst synthesis names the result a **"designed proxy sensor"** — a purpose-grown, homogeneous stand that the coarse satellite pixel can read cleanly, standing in as a [[Covariate]] for the target crop's condition.

## Why it matters

Route B's main weakness is that it *assumes* a found patch covaries with the target crop (see the validation warning in [[Route B - Homogeneous Patch Proxy]]). The control-stand variant turns that assumption into a measurement: by planting a known covarying species under controlled, homogeneous conditions, the project can collect [[Ground Truth]] on the actual covariation and on the target crop's [[Crop Water Stress]] response, rather than inferring it indirectly. This is the variant's central advantage — it converts an article of faith into an experimental quantity.

## Role in this methodology

The control stand is an experimental sub-route under [[Route B - Homogeneous Patch Proxy]]. It draws on the [[Ground Sensing Layer]] for in-field measurement and would be exercised through the [[Validation and Field Trial Layer]], which is where the measured covariation would be established. It remains a complement to, not a replacement for, the rigorous [[Route A - Direct Probabilistic Fusion]].

## Maturity and caveats

> [!warning] Seed-stage concept — feasibility is inference
> The narrative itself frames this as a seed idea, not a committed design. Its practical feasibility (which species, plot layout, lead time before signals are usable, cost) is **not specified in the sources** and is treated here as *(inference)* pending project decisions. Confidence is therefore medium and maturity is `concept`.

> [!note] Validation is the open question
> How the control-stand covariation with the target crop is validated scientifically is the explicit open question RQ9, tracked under [[Validation Risks]].

## Source grounding

The seed idea and the "designed proxy sensor" framing are stated in `methodology_idea.txt` and `prompt.txt §4` respectively. No species, planting protocol, crop, site, or timeline is asserted beyond the sources, because none is given.
