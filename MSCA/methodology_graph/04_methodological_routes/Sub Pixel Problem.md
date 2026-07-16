---
id: METH-ROUTE-005
title: "Sub Pixel Problem"
node_type: methodology_problem
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
  - "methodology_idea.txt (sub-pixel: small horticultural plot < pixel)"
  - "prompt.txt §2 (sub-pixel problem & downscaling critique)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes:
  - "[[Diagnostic Branch]]"
downstream_nodes:
  - "[[Downscaling Critique]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
related_nodes:
  - "[[Core Architecture]]"
key_terms:
  - "[[Covariate]]"
  - "[[Downscaling]]"
  - "[[PlanetScope]]"
  - "[[Sentinel 2]]"
  - "[[SAR]]"
risks: []
open_questions:
  - "How small are the target horticultural plots relative to available pixel sizes? (RQ3, RQ8)"
validation_needs:
  - "Quantify the pixel-to-plot size ratio for candidate fields and sensors"
aliases:
  - "Sub-pixel problem"
  - "Mixed pixel problem"
tags:
  - methodology-graph
  - route
  - terminology
---

# Sub Pixel Problem

The core obstacle to using satellite data directly for small horticultural fields: at today's resolutions a single plot is smaller than one image pixel, so the pixel mostly senses its surroundings rather than the plot itself.

> [!note] Definition
> The **sub-pixel problem** (also called the **mixed pixel problem**) arises when the target of interest — here, a small horticultural plot — is smaller than the ground footprint of a satellite image pixel. The pixel value is then a blend dominated by the *surrounding area* (neighbouring fields, bare soil, roads, buildings), not by the plot under study. In the words of the design narrative, "at today's resolutions a small horticultural plot is sub-pixel: the pixel sees mostly the surrounding area, not the plot itself."

## What it is

A satellite pixel reports one aggregate value over its ground footprint. When a plot occupies only a fraction of that footprint, the measured signal is a *mixture* of the plot and everything else inside the pixel. The plot's true condition is therefore confounded with neighbouring land cover, and the raw pixel cannot be taken as an observation of the plot. This is why the satellite "cannot be used as is" for the diagnostic task — it must be handled by a deliberate methodological choice rather than read off directly.

## Role in this methodology

The sub-pixel problem is the hinge on which the project's two methodological routes turn. It sits downstream of the [[Diagnostic Branch]] (which needs an honest estimate of the [[Latent Field State]]) and upstream of the design choices that respond to it. Three distinct responses branch from this node:

- The "obvious" response — multi-step [[Downscaling]] — is examined and critiqued in the [[Downscaling Critique]].
- [[Route A - Direct Probabilistic Fusion]] *solves* the problem by feeding the satellite as one more [[Covariate]] straight into a probabilistic model, with no intermediate pixel to reconstruct.
- [[Route B - Homogeneous Patch Proxy]] *sidesteps* the problem by choosing a larger, homogeneous patch the coarse pixel can read cleanly.

The problem is most acute for the lower-resolution sensors ([[Sentinel 2]] optical, [[Sentinel 1]] [[SAR]]); higher-resolution imagery such as [[PlanetScope]] can ease but not eliminate it for very small plots. It links back up to the overall [[Core Architecture]].

## Source grounding

The framing is stated directly in the PI/colleague design narrative (`methodology_idea.txt`) and reproduced in the analyst synthesis (`prompt.txt §2`). The specific composition of a mixed pixel (crop plus neighbouring fields, soil, roads, buildings) elaborates the sources' "surrounding area" with standard remote-sensing terminology *(inference for clarity, not new fact)*.

## Open questions

The exact plot-to-pixel size ratio for the project's candidate fields and sensors is not specified in the sources and depends on the chosen crop and field selection (relates to RQ3 and RQ8). See [[Diagnostic Branch]] and [[Route Comparison]] for how this feeds downstream choices.
