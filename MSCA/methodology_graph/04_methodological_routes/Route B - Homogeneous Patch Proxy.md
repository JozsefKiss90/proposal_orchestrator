---
id: METH-ROUTE-002
title: "Route B - Homogeneous Patch Proxy"
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
  - "methodology_idea.txt (the creative/easier patch route: close homogeneous patch matched on high-res soil/climate, biology covaries with crop; coarse pixel reads directly, nothing to disaggregate; ecosystem co-benefit; could turn out even better)"
  - "prompt.txt §4 (Route 2 patch/biological proxy; easier to pilot; needs covariation validation)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes:
  - "[[Sub Pixel Problem]]"
downstream_nodes:
  - "[[AquaCrop Decision Interface]]"
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Control Stand Variant]]"
  - "[[Route Comparison]]"
  - "[[Ground Sensing Layer]]"
  - "[[Validation Risks]]"
key_terms:
  - "[[Covariate]]"
  - "[[Ground Truth]]"
  - "[[Crop Water Stress]]"
risks:
  - "[[Validation Risks]]"
open_questions:
  - "How will the homogeneous-patch covariation with the target crop be validated scientifically? (RQ9)"
  - "Will Route B be a fallback/comparison or implemented alongside Route A? (RQ2)"
validation_needs:
  - "Demonstrate that the chosen patch really covaries with the target crop"
aliases:
  - "Route 2"
  - "Patch route"
  - "Biological proxy route"
tags:
  - methodology-graph
  - route
---

# Route B - Homogeneous Patch Proxy

The "creative and easier" route: rather than solving the [[Sub Pixel Problem]], sidestep it by choosing a nearby homogeneous patch whose biology covaries with the target crop and which the coarse pixel can read cleanly.

## What it is

Where [[Route A - Direct Probabilistic Fusion]] *solves* the resolution problem, Route B "sidesteps the resolution problem rather than solving it." The idea, in the design narrative's words, is to "select a close, homogeneous patch, matched on our high-resolution soil and climate data, whose biology covariates with the chosen crop, so that similar conditions give similar effect; a clean patch like this the coarse pixel can read directly, with nothing to disaggregate."

Because the patch is large and homogeneous enough to fill a pixel, there is no mixed-pixel signal to untangle and no reconstruction step — so the route avoids the multiplicative-error concern raised in the [[Downscaling Critique]] entirely, from the other direction.

## How the proxy works

The patch acts as a biological proxy ([[Covariate]]) for the target crop's condition:

1. Use high-resolution soil and climate data to find a close patch matched on growing conditions.
2. Require that the patch's biology **covaries** with the chosen crop — "similar conditions give similar effect."
3. Read the patch directly from the coarse satellite pixel, and infer the target crop's [[Crop Water Stress]] / state from the covarying signal.

The experimental extension — deliberately planting a covarying species as a "designed proxy sensor" so that covariation can be *measured* rather than *assumed* — is developed in the [[Control Stand Variant]].

## Role in this methodology

Route B is the lighter-weight alternative to Route A and feeds the same downstream pipeline: its diagnosed state passes into the [[AquaCrop Decision Interface]] ("from the diagnosed state onward the path is the same for both"). It draws on the [[Ground Sensing Layer]] for the soil/climate matching and ground measurements, and the two routes are weighed in [[Route Comparison]].

The narrative notes it "is lighter to build, and depending on where we end up — the data we have, the landscape — it could turn out even better than the hardcore route" *(the "could be better" claim is the author's expectation — treat as inference, not established fact)*.

## Ecological co-benefit

Route B "leans on keeping natural, semi-natural patches in the landscape, which sits well with the continuity of ecosystems and with extensive agriculture, and the same trick scales there once horticulture has shown the way." This connects the methodology to landscape sustainability and gives the route a strategic upside beyond the technical one.

## Validation requirement

> [!warning] Covariation must be proven, not assumed
> The route's central assumption is that the patch genuinely covaries with the target crop. The analyst synthesis flags that this "needs validation (must show the patch really covaries with the target crop)." How this covariation is established scientifically is an open question (RQ9), tracked under [[Validation Risks]] and the [[Control Stand Variant]].

## Source grounding

All claims above come from `methodology_idea.txt` and `prompt.txt §4`. No specific patch, species, crop, or site is asserted — none is given in the sources. Whether Route B is implemented alongside Route A or serves as a fallback/comparison is a project decision (RQ2; see [[Route Comparison]]).
