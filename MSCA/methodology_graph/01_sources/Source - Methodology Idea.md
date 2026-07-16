---
id: METH-SRC-002
title: "Source - Methodology Idea"
node_type: source
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
evidence_basis:
  - "sources/methodology_idea.txt"
  - "doi:10.1016/j.envsoft.2022.105556"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders:
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
upstream_nodes: []
downstream_nodes:
  - "[[Core Architecture]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[AquaCrop Decision Interface]]"
related_nodes:
  - "[[Core Architecture]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Sub Pixel Problem]]"
  - "[[Downscaling Critique]]"
  - "[[AquaCrop Decision Interface]]"
  - "[[PI Role]]"
  - "[[Methodology Graph - Meta Node]]"
key_terms:
  - "[[Data Fusion]]"
  - "[[Bayesian Hierarchical Model]]"
  - "[[Gaussian Process]]"
  - "[[Probabilistic Machine Learning]]"
  - "[[Latent Field State]]"
  - "[[Uncertainty Propagation]]"
  - "[[Counterfactual Simulation]]"
  - "[[Expected Profit]]"
  - "[[AquaCrop]]"
risks: []
open_questions:
  - "Is the first crop definitely tomato, or more broadly horticultural row crops? (RQ1)"
  - "[[Ten Research Questions]]"
validation_needs: []
aliases:
  - "methodology_idea.txt"
  - "PI Design Narrative"
tags:
  - methodology-graph
  - source
---

# Source - Methodology Idea

> [!note] Immutable source note
> This node is a faithful précis of the raw source `sources/methodology_idea.txt` — the PI/colleague's first-person **design narrative** and the primary statement of methodological intent. The raw file is immutable per [[Source - LLM Wiki Method]]; this page restates it with attribution.

One-line summary: the PI's design narrative that defines the project as a **two-branch, two-route methodology with a single uncertainty chain**, sidesteps the satellite resolution problem by predicting directly from covariates, and routes the diagnosed state through an **uncertainty-aware [[AquaCrop]]** model to a **profit-based** irrigation decision.

## What the narrative establishes

**Two branches, one chain.** The problem has a **diagnostic** branch (the actual state of field, plant, soil, water) and a **prognostic, counterfactual** branch (given that state, what happens under each decision → pick the best). The two are "tied together by one chain that carries its uncertainty from end to end," and keeping that uncertainty honest is "the heart of the whole thing" — the project's red thread of [[Uncertainty Propagation]] formalised in [[Core Architecture]] and [[Uncertainty Chain]]. The PI is explicit that **data gathering is the easy part**; the work where "the project lives or dies" is the **fusion, the modelling, the validation**.

**The satellite cannot be used as-is.** At today's resolutions a small horticultural plot is **sub-pixel** — the pixel sees mostly surrounding area, not the plot (the [[Sub Pixel Problem]]).

**The downscaling critique.** The "obvious, almost too obvious" answer is downscaling: a statistical layer ([[Cokriging]], deep learning) turns covariates into a fine pixel, then a second model turns that pixel into the prediction. Cokriging *does* carry its own uncertainty — that is **not** the issue; **the issue is the two steps**. `Covariates → pixel → prediction` **propagates error multiplicatively** (the second step inflating what the first carries) and **conditions on an estimated pixel as if it had been measured**. There is "no need to pass through the pixel": use covariates and their uncertainty **directly**, in **one step** (the [[Downscaling Critique]]).

## The two routes

> [!note] Both routes share one downstream decision engine
> "From the diagnosed state onward the path is the same for both."

- **Route A — the "hardcore" one** ([[Route A - Direct Probabilistic Fusion]]): feed the satellite as just one more input into a **probabilistic ML model** — e.g. a **[[Bayesian Hierarchical Model]]** or a **[[Gaussian Process]]** — taking satellite + sensors + soil + weather together, straight to the [[Latent Field State]] with its uncertainty. One step instead of two. "Rigorous… the harder road," leaning heavily on ML ("wants strong hands").
- **Route B — the "creative/easier" patch idea** ([[Route B - Homogeneous Patch Proxy]]): sidesteps the resolution problem rather than solving it. Select a close, **homogeneous patch** matched on high-resolution soil & climate data, whose biology covaries with the chosen crop (similar conditions → similar effect) — a clean patch the coarse pixel can read directly, nothing to disaggregate. **Seed idea:** instead of only *searching* for such a patch, deliberately **plant a control stand of a covarying species** to *measure* the covariation instead of assuming it (the [[Control Stand Variant]]). Lighter to build; depending on data/landscape "could turn out even better than the hardcore route" *(the PI states this as possibility, not fact — treated as inference downstream)*. Side benefit: it leans on keeping natural/semi-natural patches, fitting ecosystem continuity and extensive agriculture, and scales there once horticulture shows the way.

## From state to decision

Both routes calibrate a **simple [[AquaCrop]] model** ([[AquaCrop Decision Interface]]), which does two jobs: it **stands for the plant** AND is the **interface through which decisions act**. Calibration is **uncertainty-aware**, following a method the PI developed (**doi:10.1016/j.envsoft.2022.105556**) — keep "an honest range rather than one overconfident parameter set" (the [[Uncertainty Aware AquaCrop Calibration]]).

At each decision point, run the model **forward under all candidate decisions, over weather ensembles**, and steer toward the **best expected outcome at the end of the season** — the **objective being profit rather than yield**, net of water and input costs, "since the whole point is that it should pay off" (the [[Profit Based Objective Function]], a [[Counterfactual Simulation]] toward [[Expected Profit]]).

The PI starts with **horticulture, mainly irrigation** (where AquaCrop is strong); fertilization can follow.

> [!warning] Unconfirmed — first crop
> confidence: low. The PI is unsure whether the first crop is **tomato** ("do I remember right, that it would be tomato first?"). The safe framing is **horticultural row crops**; see [[AquaCrop Decision Interface]] and RQ1 in [[Ten Research Questions]]. Do not present "tomato" as a settled decision.

## Novelty claim (PI's own words)

"Up to my knowledge nobody has put exactly these pieces together quite like this" — the real edge, **"if we defend it carefully."** This intent is sharpened into the defendable [[Probabilistic Fusion Novelty Claim]] using [[Source - Literature Review]].

## Role in this methodology

This is the **primary design source** for the methodology graph: it originates [[Core Architecture]], both methodological routes, the [[Sub Pixel Problem]]/[[Downscaling Critique]] argument, and the AquaCrop decision layer. Authorship of the narrative plus the calibration DOI is the basis for the inferred [[PI Role]] and [[Methodology Contributor Role]] (names unconfirmed). Navigate up via the [[Methodology Graph - Meta Node]]; citing nodes are tracked in the [[Source Traceability Register]].

## Links & relationships
- **Feeds:** [[Core Architecture]], [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]], [[AquaCrop Decision Interface]]
- **Related:** [[Sub Pixel Problem]], [[Downscaling Critique]], [[Control Stand Variant]], [[Uncertainty Aware AquaCrop Calibration]], [[PI Role]], [[Source - Methodology Synthesis Prompt]]
- **Key terms:** [[Data Fusion]], [[Bayesian Hierarchical Model]], [[Gaussian Process]], [[Probabilistic Machine Learning]], [[Latent Field State]], [[Uncertainty Propagation]], [[Counterfactual Simulation]], [[Expected Profit]], [[AquaCrop]]
