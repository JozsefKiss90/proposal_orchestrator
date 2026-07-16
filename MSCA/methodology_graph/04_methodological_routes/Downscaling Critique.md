---
id: METH-ROUTE-004
title: "Downscaling Critique"
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
  - "methodology_idea.txt (two-step downscaling; multiplicative error; conditions on estimated pixel as if measured; one-step alternative)"
  - "prompt.txt §2 (covariates + uncertainty -> prediction directly, vs covariates -> estimated fine pixel -> prediction)"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[Methodology Contributor Role]]"
stakeholders: []
upstream_nodes:
  - "[[Sub Pixel Problem]]"
downstream_nodes:
  - "[[Route A - Direct Probabilistic Fusion]]"
related_nodes:
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Uncertainty Chain]]"
key_terms:
  - "[[Downscaling]]"
  - "[[Cokriging]]"
  - "[[Covariate]]"
  - "[[Uncertainty Propagation]]"
  - "[[Posterior Distribution]]"
risks: []
open_questions: []
validation_needs:
  - "Empirically compare one-step vs two-step error/coverage on the same data"
aliases: []
tags:
  - methodology-graph
  - route
---

# Downscaling Critique

The methodological argument against the "obvious" two-step downscaling answer to the [[Sub Pixel Problem]], and the case for a single-step alternative that uses covariates and their uncertainty directly.

## The "obvious" answer and why it is questioned

Faced with the [[Sub Pixel Problem]], the design narrative calls [[Downscaling]] "the obvious answer — almost too obvious." In the two-step form, a statistical layer (e.g. [[Cokriging]] or deep learning) first turns the [[Covariate]] inputs into an estimated fine pixel, and then a *second* model turns that estimated pixel into the field-state prediction:

`covariates → estimated fine pixel → prediction`

The critique is explicit that the problem is **not** that cokriging lacks an uncertainty estimate — "cokriging does carry its own uncertainty, so that is not the issue." The objection is to **the two steps themselves**.

## The two-step objection

Two linked problems are raised in the sources:

1. **Multiplicative error propagation.** Passing covariates → pixel → prediction "propagates the error multiplicatively — the second step inflating what the first already carries." Each stage adds and compounds uncertainty rather than merely passing it along. This is a concrete instance of poor [[Uncertainty Propagation]].
2. **Conditioning on an estimate as if it were measured.** The pipeline "conditions on an estimated pixel as if it had been measured." The second model treats a *reconstructed* quantity — itself uncertain — as though it were an observed fact, which understates how much the final prediction should be doubted and corrupts the [[Posterior Distribution]].

## The one-step alternative

The narrative's conclusion is that "there is simply no need to pass through the pixel." The covariates and their uncertainty can be used **directly** for the prediction, in one step:

`covariates + uncertainty → prediction`

This collapses the intermediate reconstruction, so there is "no intermediate pixel to inflate the error," and keeps uncertainty honest end-to-end — the project's red thread, captured in the [[Uncertainty Chain]]. The one-step principle is exactly what [[Route A - Direct Probabilistic Fusion]] operationalises: the satellite enters a probabilistic model as just one more covariate, straight to the field state with its uncertainty.

> [!note] Relationship to the two routes
> This critique motivates **Route A** directly (one-step fusion). It also bears on [[Route B - Homogeneous Patch Proxy]], which avoids the issue from the other side: by choosing a patch the coarse pixel can read cleanly, there is "nothing to disaggregate," so no reconstruction step is needed at all. The two routes are compared in [[Route Comparison]].

## Source grounding

Every claim above is stated in the PI/colleague narrative (`methodology_idea.txt`) and echoed in the analyst synthesis (`prompt.txt §2`). No external citation is asserted for the multiplicative-error claim; it is presented as the project's own methodological reasoning.

## Validation note

The one-step advantage is argued on principle in the sources. An empirical comparison — one-step vs two-step error and interval coverage on the same data — would be needed to demonstrate it, and connects to the [[Uncertainty Chain]] and validation work *(inference: not specified as a planned experiment in the sources)*.
