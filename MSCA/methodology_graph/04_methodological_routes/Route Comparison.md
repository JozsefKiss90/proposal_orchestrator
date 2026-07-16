---
id: METH-ROUTE-006
title: "Route Comparison"
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
  - "methodology_idea.txt (two routes under one thread; from diagnosed state onward path is the same; Route B lighter, could be better)"
  - "prompt.txt §10 (analyst instinct: two-route methodology with one shared decision engine; A rigorous, B fallback/comparison)"
evidence_strength: synthesis
confidence: medium
maturity: project_decision_needed
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes: []
downstream_nodes: []
related_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Control Stand Variant]]"
  - "[[Sub Pixel Problem]]"
  - "[[Downscaling Critique]]"
  - "[[Ten Research Questions]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Covariate]]"
  - "[[Uncertainty Propagation]]"
risks: []
open_questions:
  - "Will Route A and Route B both be implemented, or one main + one fallback/comparison? (RQ2)"
validation_needs:
  - "Decide and justify the route strategy (one main / one fallback, or both) for the proposal"
aliases: []
tags:
  - methodology-graph
  - route
---

# Route Comparison

A side-by-side comparison of the two methodological routes for handling the [[Sub Pixel Problem]], plus the open project decision of which to run — synthesised from the design narrative and the analyst's instinct.

> [!note] This node is a synthesis
> The comparison table below organises facts stated across the sources; the prioritisation ("A main / B fallback") is the analyst's instinct, not a settled project decision. Treat the *facts* as source-grounded and the *strategy* as a decision still to be made (RQ2).

## The shared spine

Both routes attack the same problem — the satellite "cannot be used as is" because a small horticultural plot is sub-pixel — but they diverge only at the diagnostic stage. As the narrative stresses, "from the diagnosed state onward the path is the same for both": each route's field-state estimate flows into the same uncertainty-aware AquaCrop counterfactual decision engine. The single shared thread is honest [[Uncertainty Propagation]].

- [[Route A - Direct Probabilistic Fusion]] *solves* the resolution problem (one-step probabilistic [[Data Fusion]], satellite as a [[Covariate]]); see also the [[Downscaling Critique]].
- [[Route B - Homogeneous Patch Proxy]] *sidesteps* it (a clean covarying patch the coarse pixel reads directly), with the [[Control Stand Variant]] as its experimental extension.

## Comparison table

| Dimension | Route A — Direct Probabilistic Fusion | Route B — Homogeneous Patch Proxy |
|---|---|---|
| Resolution handling | Solves it (no intermediate pixel) | Sidesteps it (clean patch, nothing to disaggregate) |
| ML / modelling burden | High — "leans heavily on the ML side"; "wants strong hands" | Lighter — "lighter to build" |
| Data needs | Multi-source fusion + good validation data | High-res soil/climate for matching; ground measurement of the patch |
| Validation needs | Uncertainty calibration; strong validation data | Must prove patch covaries with target crop (RQ9) |
| Ecological co-benefit | Not inherent | Yes — favours natural/semi-natural patches, extensive agriculture |
| Key risk | Model complexity / overconfidence ([[Model Complexity Risks]]) | Covariation assumption fails ([[Validation Risks]]) |
| Maturity | Rigorous; demanding but well-motivated | Creative; "could turn out even better" *(author's expectation — inference)* |

## The route strategy (open decision)

The analyst's instinct (prompt.txt §10) is to frame the work as a **two-route methodology with one shared decision engine**: Route A as the rigorous primary, Route B as an ecological proxy / credible fallback and comparison. This combination is presented as offering "ambition + flexibility + credible fallback." Whether to implement both, or one main plus one fallback/comparison, is the explicit open question RQ2 in the [[Ten Research Questions]].

## Source grounding

The shared-spine claim, route descriptions, and relative difficulty come from `methodology_idea.txt`; the two-routes-one-engine framing and the A-main/B-fallback instinct come from `prompt.txt §10`. No quantitative scoring is asserted — the table reflects only qualitative distinctions drawn from the sources.
